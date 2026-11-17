"""Plain metrics on results expressed in R (multiples of the initial risk)."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

EPS = 1e-9


def _arr(r) -> np.ndarray:
    a = np.asarray(r, dtype=float)
    return a[~np.isnan(a)]


def max_drawdown(r: Sequence[float]) -> float:
    """Largest peak-to-trough fall of the cumulative R curve (a positive number)."""
    a = _arr(r)
    if a.size == 0:
        return 0.0
    curve = np.concatenate([[0.0], np.cumsum(a)])
    return float(np.max(np.maximum.accumulate(curve) - curve))


def summarize_r(r: Sequence[float]) -> dict:
    """Count, mean, win/loss/breakeven rates, profit factor, drawdown, t-statistic."""
    a = _arr(r)
    n = int(a.size)
    if n == 0:
        return {"n": 0}
    wins, losses = a[a > EPS], a[a < -EPS]
    std = float(a.std(ddof=1)) if n > 1 else float("nan")
    return {
        "n": n,
        "mean": float(a.mean()),
        "median": float(np.median(a)),
        "std": std,
        "t_stat": float(a.mean() / (std / np.sqrt(n))) if n > 1 and std > 0 else float("nan"),
        "total": float(a.sum()),
        "win_rate": wins.size / n,
        "loss_rate": losses.size / n,
        "breakeven_rate": (n - wins.size - losses.size) / n,
        "profit_factor": float(wins.sum() / -losses.sum()) if losses.size else float("inf"),
        "max_drawdown": max_drawdown(a),
    }


def win_rate_by_days(times: Sequence, r: Sequence[float], tz: str = "UTC") -> dict:
    """Compare the trade win rate with the 'winning days' figure many sellers quote.

    Returns the share of winning trades, of positive days and of non-negative
    days (days at breakeven are often presented as "no losing day").
    """
    t = pd.to_datetime(pd.Series(times), utc=True).dt.tz_convert(tz)
    s = pd.Series(np.asarray(r, dtype=float), index=t.values).dropna()
    if s.empty:
        return {"trades": 0}
    days = s.groupby(pd.DatetimeIndex(s.index).date).sum()
    return {
        "trades": int(s.size),
        "trade_win_rate": float((s > EPS).mean()),
        "days": int(days.size),
        "positive_day_rate": float((days > EPS).mean()),
        "non_negative_day_rate": float((days > -EPS).mean()),
    }


def expectancy_by_period(times: Sequence, r: Sequence[float], n_periods: int = 3) -> pd.DataFrame:
    """Split the trades in ``n_periods`` consecutive blocks of equal size.

    A falling mean R from block to block is a classic sign of an edge that is
    fading or that was never there (early results flattered by luck).
    """
    t = pd.to_datetime(pd.Series(times), utc=True)
    df = pd.DataFrame({"time": t.values, "r": np.asarray(r, dtype=float)}).dropna()
    df = df.sort_values("time").reset_index(drop=True)
    if df.empty:
        return pd.DataFrame(columns=["period", "start", "end", "n", "mean_r", "total_r"])
    blocks = np.array_split(np.arange(len(df)), max(1, min(n_periods, len(df))))
    rows = []
    for k, idx in enumerate(blocks, start=1):
        part = df.iloc[idx]
        rows.append({
            "period": k,
            "start": part["time"].iloc[0],
            "end": part["time"].iloc[-1],
            "n": len(part),
            "mean_r": float(part["r"].mean()),
            "total_r": float(part["r"].sum()),
        })
    return pd.DataFrame(rows)
