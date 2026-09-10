from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.market import nearest_price
from src.ledger import account, save_account, settings, affordable_qty, fees, append_trade, new_trade_id

SHANGHAI = ZoneInfo("Asia/Shanghai")
cfg = settings()
a = account()
cand = json.loads((ROOT / "config/candidates.json").read_text(encoding="utf-8"))
today = datetime.now(SHANGHAI).strftime("%Y-%m-%d")
trade_date = cand.get("trade_date")
selected = []
notes = []

if trade_date != today:
    notes.append(f"candidate date {trade_date!r} does not equal Beijing trade date {today}; skipped")
elif cand.get("market_ok"):
    selected = [x for x in cand.get("candidates", []) if x.get("approved")][:3]
else:
    notes.append("market filter not approved; skipped")

position_cost = sum(
    int(p["quantity"]) * float(p["buy_price"]) for p in a["positions"].values()
)
total_assets = a["cash"] + position_cost
max_total_value = cfg["max_total_weight"] * total_assets
used = position_cost

for x in selected:
    code = str(x["code"]).zfill(6)
    name = x.get("name", code)
    if code in a["positions"]:
        notes.append(f"{code}: already held; skipped")
        continue
    px = nearest_price(
        code,
        trade_date,
        cfg["buy_target_time"],
        cfg["buy_window_start"],
        cfg["buy_window_end"],
        max_minutes=cfg["max_price_distance_minutes"],
    )
    if not px:
        notes.append(
            f"{code}: no verifiable 1-minute close in "
            f"{cfg['buy_window_start']}-{cfg['buy_window_end']} near {cfg['buy_target_time']}; skipped"
        )
        continue
    target = min(cfg["max_stock_weight"] * total_assets, max_total_value - used)
    qty = affordable_qty(a["cash"], px["price"], target, cfg)
    if qty <= 0:
        notes.append(f"{code}: insufficient cash or position limit; skipped")
        continue
    gross = round(qty * px["price"], 2)
    fee = fees(gross, "buy", cfg)
    a["cash"] = round(a["cash"] - gross - fee, 2)
    a["positions"][code] = {
        "name": name,
        "quantity": qty,
        "buy_price": px["price"],
        "buy_date": trade_date,
        "buy_time": px["timestamp"][11:19],
        "buy_fees": fee,
        "reason": x.get("reason", ""),
    }
    append_trade({
        "trade_id": new_trade_id(), "code": code, "name": name,
        "buy_date": trade_date, "buy_time": px["timestamp"][11:19],
        "buy_price": px["price"], "quantity": qty, "buy_gross": gross,
        "buy_fees": fee, "status": "OPEN", "reason": x.get("reason", ""),
    })
    used += gross
    notes.append(f"{code}: simulated buy {qty} @ {px['price']} ({px['timestamp']})")

save_account(a)
with (ROOT / "data/decisions.csv").open("a", newline="", encoding="utf-8") as f:
    csv.writer(f).writerow([
        today, "tail", cand.get("market_ok", False),
        "|".join(str(x.get("code")) for x in selected),
        cand.get("market_note", "") + "; " + "; ".join(notes),
    ])
print("\n".join(notes) if notes else "No approved candidates. Account unchanged.")
