from __future__ import annotations
import datetime as dt
import pandas as pd
import akshare as ak


def minute_bars(code: str, trade_date: str) -> pd.DataFrame:
    start = f"{trade_date} 09:30:00"
    end = f"{trade_date} 15:00:00"
    df = ak.stock_zh_a_hist_min_em(symbol=code, start_date=start, end_date=end, period="1", adjust="")
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["时间"] = pd.to_datetime(df["时间"])
    return df.sort_values("时间")


def nearest_price(code: str, trade_date: str, target_time: str, max_minutes: int = 5):
    df = minute_bars(code, trade_date)
    if df.empty:
        return None
    target = pd.Timestamp(f"{trade_date} {target_time}")
    delta = (df["时间"] - target).abs()
    i = delta.idxmin()
    if delta.loc[i] > pd.Timedelta(minutes=max_minutes):
        return None
    row = df.loc[i]
    return {
        "timestamp": row["时间"].strftime("%Y-%m-%d %H:%M:%S"),
        "price": float(row["收盘"]),
        "volume": float(row.get("成交量", 0) or 0),
        "amount": float(row.get("成交额", 0) or 0),
    }


def latest_spot() -> pd.DataFrame:
    df = ak.stock_zh_a_spot_em()
    return df if df is not None else pd.DataFrame()
