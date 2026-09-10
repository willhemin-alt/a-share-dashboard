from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.market import nearest_price
from src.ledger import account, save_account, settings, fees, read_trades, rewrite_trades

SHANGHAI = ZoneInfo("Asia/Shanghai")
cfg = settings()
a = account()
today = datetime.now(SHANGHAI).strftime("%Y-%m-%d")
rows = read_trades()
msgs = []

for code, pos in list(a["positions"].items()):
    if pos.get("buy_date", today) >= today:
        msgs.append(f"{code}: not an overnight position; retained")
        continue
    px = nearest_price(
        code,
        today,
        cfg["sell_target_time"],
        cfg["sell_window_start"],
        cfg["sell_window_end"],
        max_minutes=cfg["max_price_distance_minutes"],
    )
    if not px:
        msgs.append(
            f"{code}: no verifiable 1-minute close in "
            f"{cfg['sell_window_start']}-{cfg['sell_window_end']} near {cfg['sell_target_time']}; retained"
        )
        continue
    qty = int(pos["quantity"])
    gross = round(qty * px["price"], 2)
    sell_fee = fees(gross, "sell", cfg)
    buy_gross = round(qty * float(pos["buy_price"]), 2)
    total_cost = buy_gross + float(pos["buy_fees"])
    net = gross - sell_fee
    pnl = round(net - total_cost, 2)
    ret = round(pnl / total_cost * 100, 4)
    a["cash"] = round(a["cash"] + net, 2)
    a["realized_pnl"] = round(a["realized_pnl"] + pnl, 2)
    a["completed_trades"] += 1
    if pnl > 0:
        a["winning_trades"] += 1
    for row in rows:
        if row["code"] == code and row["status"] == "OPEN":
            row.update({
                "sell_date": today, "sell_time": px["timestamp"][11:19],
                "sell_price": px["price"], "sell_gross": gross,
                "sell_fees": sell_fee, "pnl": pnl,
                "return_pct": ret, "status": "CLOSED",
            })
            break
    del a["positions"][code]
    msgs.append(f"{code}: simulated sell {qty} @ {px['price']} ({px['timestamp']}); PnL {pnl:+.2f}")

rewrite_trades(rows)
save_account(a)
with (ROOT / "data/decisions.csv").open("a", newline="", encoding="utf-8") as f:
    csv.writer(f).writerow([today, "morning", "", "", "; ".join(msgs) or "No open positions"])
print("\n".join(msgs) if msgs else "No open positions.")
