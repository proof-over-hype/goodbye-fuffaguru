"""Synthetic markets with no edge by construction.

The bars follow a random walk with clustered volatility (calm hours and wild
hours, like real markets) and no drift unless you ask for one. No rule can
have a real edge on them: anything that "works" here is luck or selection.
That is exactly what makes them useful to show how easy it is to fool
yourself, and to test the tools.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def random_walk_bars(
    n_bars: int,
    *,
    start: str = "2024-01-01",
    freq: str = "15min",
    start_price: float = 2000.0,
    vol: float = 0.0015,
    drift: float = 0.0,
    vol_persistence: float = 0.98,
    vol_of_vol: float = 0.12,
    seed: int = 0,
) -> pd.DataFrame:
    """OHLC bars from a log random walk with stochastic volatility.

    vol: typical per-bar standard deviation of log returns
    drift: per-bar mean log return (0 = no trend; a positive value mimics a bull market)
    """
    rng = np.random.default_rng(seed)
    log_vol = np.zeros(n_bars)
    shocks = rng.normal(0.0, vol_of_vol, n_bars)
    for t in range(1, n_bars):
        log_vol[t] = vol_persistence * log_vol[t - 1] + shocks[t]
    sigma = vol * np.exp(log_vol - log_vol.var() / 2.0)
    rets = drift + sigma * rng.standard_normal(n_bars)
    close = start_price * np.exp(np.cumsum(rets))
    open_ = np.concatenate([[start_price], close[:-1]])
    up = np.exp(np.abs(rng.normal(0.0, 0.6, n_bars)) * sigma)
    down = np.exp(-np.abs(rng.normal(0.0, 0.6, n_bars)) * sigma)
    high = np.maximum(open_, close) * up
    low = np.minimum(open_, close) * down
    index = pd.date_range(start=start, periods=n_bars, freq=freq, tz="UTC", name="time")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=index)
