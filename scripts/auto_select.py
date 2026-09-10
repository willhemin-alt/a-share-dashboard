from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "candidates.json"
HISTORY = ROOT / "data" / "selection_history.json"
BEIJING = ZoneInfo("Asia/Shanghai")


def number(series):
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def fail(date: str, reason: str):
    result = {
        "trade_date": date,
        "market_ok": False,
        "market_note": reason,
        "method": "automatic_market_evidence_v1",
        "candidates": [],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(reason)


def main():
    now = datetime.now(BEIJING)
    date = now.strftime("%Y-%m-%d")
    compact = now.strftime("%Y%m%d")
    if now.weekday() >= 5:
        fail(date, "北京时间为周末，主动空仓")
        return

    try:
        spot = ak.stock_zh_a_spot_em()
        limits = ak.stock_zt_pool_em(date=compact)
    except Exception as exc:
        fail(date, f"自动筛选行情接口失败：{type(exc).__name__}: {exc}")
        return
    required_spot = {"代码", "名称", "涨跌幅", "成交额", "换手率", "总市值"}
    if spot is None or spot.empty or not required_spot.issubset(spot.columns):
        fail(date, "全市场行情缺失必要字段，主动空仓")
        return
    if limits is None or limits.empty or "所属行业" not in limits.columns:
        fail(date, "当日涨停池或行业字段缺失，主动空仓")
        return

    spot = spot.copy()
    spot["代码"] = spot["代码"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    for col in ["涨跌幅", "成交额", "换手率", "总市值"]:
        spot[col] = number(spot[col])
    up = int((spot["涨跌幅"] > 0).sum())
    down = int((spot["涨跌幅"] < 0).sum())
    breadth = up / max(up + down, 1)
    limit_count = len(limits)
    cfg = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))
    if breadth < cfg["selection_min_breadth"] or limit_count < cfg["selection_min_limit_up_count"]:
        fail(
            date,
            f"市场过滤未通过：上涨{up}家、下跌{down}家、上涨占比{breadth:.1%}、涨停{limit_count}只",
        )
        return

    sectors = (
        limits["所属行业"].fillna("").astype(str).str.strip().value_counts()
    )
    sectors = sectors[
        (sectors.index != "") & (sectors >= cfg["selection_min_sector_limit_ups"])
    ]
    if sectors.empty or "所属行业" not in spot.columns:
        fail(date, f"市场通过，但没有形成至少{cfg['selection_min_sector_limit_ups']}只涨停的同行业线索")
        return

    history = []
    if HISTORY.exists():
        try:
            history = json.loads(HISTORY.read_text(encoding="utf-8"))
        except Exception:
            history = []
    recent_sectors = {
        sector
        for day in history[-cfg["selection_sector_cooldown_days"]:]
        for sector in day.get("sectors", [])
    }

    picked = []
    used_sectors = []
    for sector, sector_limits in sectors.items():
        if sector in recent_sectors:
            continue
        pool = spot[
            (spot["所属行业"].astype(str).str.strip() == sector)
            & (~spot["代码"].isin(limits["代码"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)))
            & (~spot["名称"].astype(str).str.contains(r"ST|退", regex=True))
            & (spot["涨跌幅"] >= cfg["selection_min_change_pct"])
            & (spot["涨跌幅"] <= cfg["selection_max_change_pct"])
            & (spot["换手率"] >= cfg["selection_min_turnover_pct"])
            & (spot["成交额"] >= cfg["selection_min_amount"])
            & (spot["总市值"] > 0)
        ].copy()
        if pool.empty:
            continue
        # Prefer a liquid, recognizable capacity name that has already responded,
        # rather than the weakest laggard or an already exhausted leader.
        pool["_score"] = (
            pool["成交额"].rank(pct=True) * 0.45
            + pool["总市值"].rank(pct=True) * 0.30
            + pool["涨跌幅"].rank(pct=True) * 0.15
            + pool["换手率"].rank(pct=True) * 0.10
        )
        row = pool.sort_values(["_score", "成交额"], ascending=False).iloc[0]
        code = str(row["代码"])
        reason = (
            f"{sector}有{int(sector_limits)}只涨停形成板块线索；"
            f"{row['名称']}未涨停但上涨{row['涨跌幅']:.2f}%，"
            f"成交额{row['成交额']/100000000:.2f}亿元、换手{row['换手率']:.2f}%，"
            "属于同行业中已有资金确认的高流动性候选"
        )
        picked.append({
            "code": code,
            "name": str(row["名称"]),
            "approved": True,
            "sector": sector,
            "reason": reason,
            "evidence": {
                "sector_limit_ups": int(sector_limits),
                "change_pct": round(float(row["涨跌幅"]), 4),
                "turnover_pct": round(float(row["换手率"]), 4),
                "amount": round(float(row["成交额"]), 2),
                "market_cap": round(float(row["总市值"]), 2),
            },
        })
        used_sectors.append(sector)
        if len(picked) >= cfg["selection_max_candidates"]:
            break

    market_note = (
        f"市场过滤通过：上涨{up}家、下跌{down}家、上涨占比{breadth:.1%}、"
        f"涨停{limit_count}只；按批量涨停行业反推未涨停容量候选"
    )
    result = {
        "trade_date": date,
        "generated_at": now.isoformat(timespec="seconds"),
        "market_ok": bool(picked),
        "market_note": market_note if picked else market_note + "；但无股票通过个股过滤，主动空仓",
        "method": "automatic_market_evidence_v1",
        "candidates": picked,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    history.append({"date": date, "sectors": used_sectors, "codes": [x["code"] for x in picked]})
    HISTORY.write_text(json.dumps(history[-30:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
