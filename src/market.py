from __future__ import annotations

import pandas as pd
import akshare as ak


def minute_bars(code: str, trade_date: str) -> pd.DataFrame:
    """Return unadjusted one-minute bars for one A-share trading day."""
    start = f"{trade_date} 09:30:00"
    end = f"{trade_date} 15:00:00"
    try:
        df = ak.stock_zh_a_hist_min_em(
            symbol=str(code).zfill(6),
            start_date=start,
            end_date=end,
            period="1",
            adjust="",
        )
    except Exception as exc:
        print(f"AKShare minute query failed for {code}: {type(exc).__name__}: {exc}")
        return pd.DataFrame()
    if df is None or df.empty or "时间" not in df.columns or "收盘" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["时间"] = pd.to_datetime(df["时间"], errors="coerce")
    df["收盘"] = pd.to_numeric(df["收盘"], errors="coerce")
    df = df.dropna(subset=["时间", "收盘"])
    df = df[df["时间"].dt.strftime("%Y-%m-%d") == trade_date]
    return df.sort_values("时间").reset_index(drop=True)


def nearest_price(
    code: str,
    trade_date: str,
    target_time: str,
    window_start: str,
    window_end: str,
    max_minutes: int = 5,
):
    """Return a real minute close only when it is inside the declared window."""
    df = minute_bars(code, trade_date)
    if df.empty:
        return None
    start = pd.Timestamp(f"{trade_date} {window_start}")
    end = pd.Timestamp(f"{trade_date} {window_end}")
    target = pd.Timestamp(f"{trade_date} {target_time}")
    eligible = df[(df["时间"] >= start) & (df["时间"] <= end)].copy()
    eligible = eligible[eligible["收盘"] > 0]
    if eligible.empty:
        return None
    eligible["_delta"] = (eligible["时间"] - target).abs()
    row = eligible.loc[eligible["_delta"].idxmin()]
    if row["_delta"] > pd.Timedelta(minutes=max_minutes):
        return None
    return {
        "timestamp": row["时间"].strftime("%Y-%m-%d %H:%M:%S"),
        "price": float(row["收盘"]),
        "volume": float(row.get("成交量", 0) or 0),
        "amount": float(row.get("成交额", 0) or 0),
    }


def latest_spot() -> pd.DataFrame:
    try:
        df = ak.stock_zh_a_spot_em()
    except Exception as exc:
        print(f"AKShare spot query failed: {type(exc).__name__}: {exc}")
        return pd.DataFrame()
    return df if df is not None else pd.DataFrame()
