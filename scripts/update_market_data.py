#!/usr/bin/env python3
"""Update the dashboard snapshot from public A-share market data.

The script deliberately keeps the portfolio ledger separate from market data:
screening signals may change every run, but trades only change through an
explicit simulated execution.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time as time_module
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = ROOT / "data" / "dashboard.json"
PORTFOLIO_PATH = ROOT / "data" / "portfolio_state.json"
POSITIONS_PATH = ROOT / "data" / "positions.csv"
HISTORY_PATH = ROOT / "data" / "account_history.json"
BEIJING = ZoneInfo("Asia/Shanghai")
LUXEMBOURG = ZoneInfo("Europe/Luxembourg")

INDEX_NAMES = ["上证指数", "深证成指", "创业板指", "科创50"]
WATCH_CODES = ["000568", "600036", "600900"]
TECH_KEYWORDS = (
    "人工智能", "AI", "算力", "数据", "软件", "半导体", "芯片", "通信",
    "机器人", "消费电子", "光模块", "云计算", "网络安全",
)


def pick_column(frame: pd.DataFrame, *names: str) -> str:
    for name in names:
        if name in frame.columns:
            return name
    raise KeyError(f"Missing columns {names}; received {list(frame.columns)}")


def number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def signed_pct(value: Any) -> str:
    parsed = number(value)
    return f"{parsed:+.2f}%"


def amount_yi(value: Any) -> str:
    parsed = number(value) / 100_000_000
    if parsed >= 10000:
        return f"{parsed / 10000:.2f} 万亿"
    return f"{parsed:.2f} 亿"


def load_snapshot() -> dict[str, Any]:
    return json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))


def find_row(frame: pd.DataFrame, column: str, value: str) -> pd.Series:
    rows = frame[frame[column].astype(str).str.strip() == value]
    if rows.empty:
        raise LookupError(f"Could not find {value!r} in {column}")
    return rows.iloc[0]


def update_indices(snapshot: dict[str, Any], index_frame: pd.DataFrame) -> list[float]:
    name_col = pick_column(index_frame, "名称", "指数名称")
    value_col = pick_column(index_frame, "最新价", "最新")
    change_col = pick_column(index_frame, "涨跌幅")
    changes: list[float] = []
    updated = []
    for old in snapshot["indices"]:
        row = find_row(index_frame, name_col, old["name"])
        change = number(row[change_col])
        changes.append(change)
        updated.append(
            {
                **old,
                "value": f"{number(row[value_col]):,.2f}",
                "change": signed_pct(change),
            }
        )
    snapshot["indices"] = updated
    return changes


def update_watchlist(snapshot: dict[str, Any], stock_frame: pd.DataFrame) -> None:
    code_col = pick_column(stock_frame, "代码", "序号")
    price_col = pick_column(stock_frame, "最新价")
    change_col = pick_column(stock_frame, "涨跌幅")
    amount_col = pick_column(stock_frame, "成交额")

    rows_by_code = {
        normalize_code(row[code_col]): row
        for _, row in stock_frame.iterrows()
        if normalize_code(row[code_col]) in WATCH_CODES
    }
    for stock in snapshot["watchlist"]:
        row = rows_by_code.get(stock["code"])
        if row is None:
            continue
        stock["price"] = f"{number(row[price_col]):.2f}"
        stock["change"] = signed_pct(row[change_col])
        stock["turnover"] = amount_yi(row[amount_col])


def normalize_code(value: Any) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(6)


def update_portfolios(stock_frame: pd.DataFrame, now: datetime) -> dict[str, Any]:
    portfolio = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
    code_col = pick_column(stock_frame, "代码", "序号")
    price_col = pick_column(stock_frame, "最新价")
    rows_by_code = {
        normalize_code(row[code_col]): row
        for _, row in stock_frame.iterrows()
    }
    position_rows: list[dict[str, Any]] = []
    updated_utc = now.astimezone(ZoneInfo("UTC")).isoformat(timespec="seconds")

    for account in portfolio["accounts"]:
        market_value = 0.0
        holdings = account.get("holdings", [])
        for holding in holdings:
            row = rows_by_code.get(holding["symbol"])
            if row is not None:
                latest_price = number(row[price_col])
                if latest_price > 0:
                    holding["last_price"] = round(latest_price, 4)
            holding["market_value"] = round(
                holding["quantity"] * holding["last_price"], 2
            )
            holding["unrealized_pnl"] = round(
                holding["market_value"]
                - holding["quantity"] * holding["average_cost"],
                2,
            )
            market_value += holding["market_value"]
            position_rows.append(
                {
                    "account_id": account["id"],
                    "symbol": holding["symbol"],
                    "name": holding["name"],
                    "quantity": holding["quantity"],
                    "average_cost": holding["average_cost"],
                    "last_price": holding["last_price"],
                    "market_value": holding["market_value"],
                    "unrealized_pnl": holding["unrealized_pnl"],
                    "updated_at_utc": updated_utc,
                }
            )
        account["positions"] = len(holdings)
        account["market_value"] = round(market_value, 2)
        account["equity"] = round(account["cash"] + market_value, 2)
        account["pnl"] = round(account["equity"] - account["initial_cash"], 2)
        account["pnl_pct"] = round(
            account["pnl"] / account["initial_cash"] * 100, 6
        )

    portfolio["updated_at"] = now.isoformat(timespec="seconds")
    PORTFOLIO_PATH.write_text(
        json.dumps(portfolio, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with POSITIONS_PATH.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "account_id", "symbol", "name", "quantity", "average_cost",
            "last_price", "market_value", "unrealized_pnl", "updated_at_utc",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(position_rows)
    return portfolio


def update_account_history(
    portfolio: dict[str, Any], now: datetime, mode: str
) -> None:
    # Open, morning and 14:50 prices are observations, not formal daily NAV.
    # A manual run after the 15:00 close is the only mode allowed to settle it.
    if mode != "manual" or now.time() < time(15, 0):
        return
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    account = next(
        item for item in portfolio["accounts"] if item["id"] == history["account_id"]
    )
    if not account.get("holdings"):
        return
    holding = account["holdings"][0]
    valuation = next((event for event in history["events"] if (
        event["type"] == "valuation" and event["date"] == now.date().isoformat()
    )), None)
    if valuation is None:
        valuation = {"type": "valuation"}
        history["events"].append(valuation)
    latest_trade = next((event for event in reversed(history["events"]) if (
        event["type"] == "trade"
    )), None)
    latest_trade_date = latest_trade["date"] if latest_trade else "建仓"
    valuation.update(
        {
            "date": now.date().isoformat(),
            "title": "正式收盘结算",
            "action": "持有",
            "symbol": holding["symbol"],
            "name": holding["name"],
            "quantity": holding["quantity"],
            "price": holding["last_price"],
            "gross_amount": holding["market_value"],
            "fees": 0.0,
            "cash_after": account["cash"],
            "equity_after": account["equity"],
            "note": (
                f"{latest_trade_date}后无新增正式成交；累计盈亏为 "
                f"{account['pnl']:+,.2f} 元（{account['pnl_pct']:+.2f}%）。"
            ),
        }
    )
    HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_tech(snapshot: dict[str, Any], board_frame: pd.DataFrame) -> None:
    name_col = pick_column(board_frame, "板块名称", "名称")
    change_col = pick_column(board_frame, "涨跌幅")
    amount_col = next((name for name in ("成交额", "总市值") if name in board_frame.columns), None)
    candidates = board_frame[
        board_frame[name_col].astype(str).apply(lambda name: any(key in name for key in TECH_KEYWORDS))
    ].copy()
    if candidates.empty:
        return

    candidates["_change"] = pd.to_numeric(candidates[change_col], errors="coerce").fillna(0)
    if amount_col:
        candidates["_amount"] = pd.to_numeric(candidates[amount_col], errors="coerce").fillna(0)
        max_amount = max(number(candidates["_amount"].max()), 1)
    else:
        candidates["_amount"] = 0
        max_amount = 1
    candidates["_score"] = (
        52
        + candidates["_change"] * 8
        + candidates["_amount"].apply(lambda value: 10 * math.sqrt(max(number(value), 0) / max_amount))
    ).clip(20, 95)
    candidates = candidates.sort_values(["_score", "_change"], ascending=False).head(4)

    themes = []
    for _, row in candidates.iterrows():
        score = int(round(number(row["_score"])))
        change = number(row["_change"])
        tone = "hot" if score >= 75 else "warm" if score >= 60 else "cool"
        status = "强势活跃" if change >= 1.5 else "热度上升" if change > 0 else "短线降温"
        themes.append(
            {
                "name": str(row[name_col]),
                "score": score,
                "status": status,
                "note": f"板块涨跌 {change:+.2f}%，按涨幅与成交活跃度评分",
                "tone": tone,
            }
        )
    snapshot["tech_themes"] = themes


def derive_summary(snapshot: dict[str, Any], index_changes: list[float]) -> None:
    up = snapshot["breadth"]["up"]
    down = snapshot["breadth"]["down"]
    total = max(up + down, 1)
    average = sum(index_changes) / max(len(index_changes), 1)
    score = round(50 + ((up - down) / total) * 22 + average * 4)
    score = max(20, min(85, score))
    label = "偏积极" if score >= 65 else "中性" if score >= 48 else "偏谨慎"
    leader = snapshot["tech_themes"][0]["name"] if snapshot["tech_themes"] else "科技板块"
    direction = "整体偏强" if average > 0 else "冲高承压"
    snapshot["temperature"] = {
        "score": score,
        "label": label,
        "position_note": "强势股只做确认，不追一致性高潮" if score < 65 else "顺势但控制单笔仓位",
    }
    snapshot["headline"] = f"指数{direction}，{leader}热度领先。"
    snapshot["summary"] = (
        f"全市场上涨 {up:,} 家、下跌 {down:,} 家。"
        f"科技方向当前由{leader}领跑，策略上继续区分信号与正式成交。"
    )


def fetch_market_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            stock_frame = ak.stock_zh_a_spot_em()
            index_frame = ak.stock_zh_index_spot_em()
            board_frame = ak.stock_board_concept_name_em()
            return stock_frame, index_frame, board_frame
        except Exception as exc:
            last_error = exc
            print(f"Market data attempt {attempt}/3 failed: {exc}")
            if attempt < 3:
                time_module.sleep(attempt * 10)
    assert last_error is not None
    raise last_error


def update_snapshot(mode: str) -> None:
    snapshot = load_snapshot()
    try:
        stock_frame, index_frame, board_frame = fetch_market_frames()
    except Exception as exc:
        print(
            "Market data remained unavailable after three attempts; "
            f"keeping the last verified dashboard snapshot. Error: {exc}"
        )
        return

    price_change_col = pick_column(stock_frame, "涨跌幅")
    stock_changes = pd.to_numeric(stock_frame[price_change_col], errors="coerce")
    snapshot["breadth"] = {
        "up": int((stock_changes > 0).sum()),
        "down": int((stock_changes < 0).sum()),
    }
    amount_col = pick_column(stock_frame, "成交额")
    total_amount = number(pd.to_numeric(stock_frame[amount_col], errors="coerce").sum())
    snapshot["turnover"]["display"] = f"{total_amount / 1_000_000_000_000:.2f}"
    snapshot["turnover"]["unit"] = "万亿元"

    index_changes = update_indices(snapshot, index_frame)
    update_watchlist(snapshot, stock_frame)
    update_tech(snapshot, board_frame)
    derive_summary(snapshot, index_changes)

    now = datetime.now(BEIJING)
    snapshot["as_of"] = now.date().isoformat()
    snapshot["session"] = mode
    snapshot["session_time"] = now.strftime("%H:%M")
    snapshot["timezone"] = "Asia/Shanghai"
    snapshot["generated_at"] = now.isoformat(timespec="seconds")
    DASHBOARD_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    portfolio = update_portfolios(stock_frame, now)
    update_account_history(portfolio, now, mode)
    print(f"Updated {DASHBOARD_PATH} for {mode} at {now.isoformat()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("open-check", "luxembourg-morning", "close-decision", "manual"),
        default="manual",
    )
    parser.add_argument("--require-lux-hour", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.require_lux_hour is not None:
        lux_now = datetime.now(LUXEMBOURG)
        if lux_now.hour != args.require_lux_hour:
            print(f"Skip: Europe/Luxembourg hour is {lux_now.hour}, expected {args.require_lux_hour}.")
            return
    if datetime.now(BEIJING).weekday() >= 5:
        print("Skip: weekend in China.")
        return
    update_snapshot(args.mode)


if __name__ == "__main__":
    main()
