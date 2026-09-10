from __future__ import annotations
import csv, json, math, uuid
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "config"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def settings(): return load_json(CONFIG / "settings.json")
def account(): return load_json(DATA / "account.json")
def save_account(a): save_json(DATA / "account.json", a)

def fees(gross: float, side: str, cfg: Dict) -> float:
    commission = max(cfg["minimum_commission"], gross * cfg["commission_rate"])
    transfer = gross * cfg["transfer_fee_rate"]
    stamp = gross * cfg["sell_stamp_tax_rate"] if side == "sell" else 0.0
    return round(commission + transfer + stamp, 2)

def affordable_qty(cash: float, price: float, target_value: float, cfg: Dict) -> int:
    lot = 100
    qty = int(min(cash, target_value) // price // lot * lot)
    while qty >= lot:
        gross = qty * price
        if gross + fees(gross, "buy", cfg) <= cash:
            return qty
        qty -= lot
    return 0

def append_trade(row: Dict):
    path = DATA / "trades.csv"
    fields = ["trade_id","code","name","buy_date","buy_time","buy_price","quantity","buy_gross","buy_fees","sell_date","sell_time","sell_price","sell_gross","sell_fees","pnl","return_pct","status","reason"]
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writerow({k: row.get(k, "") for k in fields})

def read_trades():
    path = DATA / "trades.csv"
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))

def rewrite_trades(rows):
    path = DATA / "trades.csv"
    fields = ["trade_id","code","name","buy_date","buy_time","buy_price","quantity","buy_gross","buy_fees","sell_date","sell_time","sell_price","sell_gross","sell_fees","pnl","return_pct","status","reason"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def new_trade_id(): return uuid.uuid4().hex[:12]
