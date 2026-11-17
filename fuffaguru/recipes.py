"""A generic, mechanical "trade the level" recipe.

Most social-media methods share one skeleton: mark a level (a swing high or
low, a "zone", an "order block"), wait for the price to come back, enter
against it with a stop just beyond and a target in R. This module implements
that skeleton with explicit numbers, so it can be preregistered, run on real
or fake levels, and compared with the random-direction null.

Everything is computed from information available *before* the entry bar
(swings are confirmed only ``k`` bars after the extreme), to avoid look-ahead.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from .trades import mirror, simulate_path


def atr(high, low, close, n: int = 14) -> np.ndarray:
    """Simple moving average of the true range (NaN for the first n-1 bars)."""
    high, low, close = (np.asarray(x, dtype=float) for x in (high, low, close))
    prev = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))
    out = np.full(tr.shape, np.nan)
    if tr.size >= n:
        csum = np.cumsum(np.insert(tr, 0, 0.0))
        out[n - 1:] = (csum[n:] - csum[:-n]) / n
    return out


def sma(x, n: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = np.full(x.shape, np.nan)
    if x.size >= n:
        csum = np.cumsum(np.insert(x, 0, 0.0))
        out[n - 1:] = (csum[n:] - csum[:-n]) / n
    return out


def swing_levels(bars: pd.DataFrame, k: int = 5, atr_n: int = 14) -> pd.DataFrame:
    """Swing highs and lows with k bars on each side.

    A swing high at bar i is a high strictly above the k highs before and not
    below the k highs after. It becomes known only at bar i + k
    (``confirmed_idx``). ``scale`` is the ATR at confirmation, used for stops
    and for shifting fake levels.
    """
    h, lo, c = (bars[col].to_numpy(dtype=float) for col in ("high", "low", "close"))
    n = len(h)
    a = atr(h, lo, c, atr_n)
    rows = []
    if n < 2 * k + 1:
        return pd.DataFrame(columns=["price", "kind", "origin_idx", "confirmed_idx", "scale"])
    win_h = sliding_window_view(h, 2 * k + 1)
    win_l = sliding_window_view(lo, 2 * k + 1)
    centre_h = win_h[:, k]
    centre_l = win_l[:, k]
    is_high = (centre_h > win_h[:, :k].max(axis=1)) & (centre_h >= win_h[:, k + 1:].max(axis=1))
    is_low = (centre_l < win_l[:, :k].min(axis=1)) & (centre_l <= win_l[:, k + 1:].min(axis=1))
    for kind, mask, prices in (("high", is_high, centre_h), ("low", is_low, centre_l)):
        for j in np.flatnonzero(mask):
            i = j + k
            conf = i + k
            if conf < n and not np.isnan(a[conf]):
                rows.append((float(prices[j]), kind, int(i), int(conf), float(a[conf])))
    df = pd.DataFrame(rows, columns=["price", "kind", "origin_idx", "confirmed_idx", "scale"])
    return df.sort_values("confirmed_idx", kind="stable").reset_index(drop=True)


@dataclass
class LevelRecipe:
    """Fade the first return to a level, with every threshold written down.

    stop_atr: stop distance in ATR (ATR of the bar before the entry)
    target_r: target in R
    breakeven_at_r: move the stop to the entry after this many R (None = never)
    max_bars: time limit of a trade, in bars
    max_age: a level older than this (in bars) is no longer traded
    trend_bars: the "key filter" - trade only in the direction of the close
        relative to its simple moving average of this length (None = no filter)
    cost: round-trip cost in price units
    """

    stop_atr: float = 1.0
    target_r: float = 1.0
    breakeven_at_r: Optional[float] = None
    max_bars: int = 96
    max_age: int = 960
    trend_bars: Optional[int] = None
    cost: float = 0.0
    atr_n: int = 14

    def to_dict(self) -> dict:
        return asdict(self)

    def run(self, bars: pd.DataFrame, levels: pd.DataFrame, prices: Optional[np.ndarray] = None) -> pd.DataFrame:
        """Run the recipe and return one row per trade.

        ``prices`` replaces ``levels['price']`` (used by the fake-level test);
        everything else about the levels (kind, timing, scale) is unchanged.
        """
        h, lo, c = (bars[col].to_numpy(dtype=float) for col in ("high", "low", "close"))
        n = len(h)
        a = atr(h, lo, c, self.atr_n)
        trend = sma(c, self.trend_bars) if self.trend_bars else None
        prices = levels["price"].to_numpy(dtype=float) if prices is None else np.asarray(prices, dtype=float)
        rows = []
        for p, kind, conf in zip(prices, levels["kind"].to_numpy(), levels["confirmed_idx"].to_numpy()):
            lo_j, hi_j = int(conf) + 1, min(n, int(conf) + 1 + self.max_age)
            if lo_j >= n - 1:
                continue
            seg_h, seg_l, prev_c = h[lo_j:hi_j], lo[lo_j:hi_j], c[lo_j - 1:hi_j - 1]
            touch = (seg_l <= p) & (seg_h >= p)
            touch &= (prev_c < p) if kind == "high" else (prev_c > p)
            hit = np.flatnonzero(touch)
            if hit.size == 0:
                continue
            j = lo_j + int(hit[0])
            side = "short" if kind == "high" else "long"
            if trend is not None:
                ref = trend[j - 1]
                if np.isnan(ref) or (side == "short" and c[j - 1] >= ref) or (side == "long" and c[j - 1] <= ref):
                    continue
            scale = a[j - 1]
            if not scale > 0:
                continue
            d = self.stop_atr * scale
            sign = 1.0 if side == "long" else -1.0
            stop, target = p - sign * d, p + sign * self.target_r * d
            end = min(n, j + self.max_bars)
            kw = dict(breakeven_at_r=self.breakeven_at_r, first_bar_stop_only=True)
            res = simulate_path(h[j:end], lo[j:end], c[j:end], side, p, stop, target, **kw)
            m_side, m_stop, m_target = mirror(side, p, stop, target)
            flip = simulate_path(h[j:end], lo[j:end], c[j:end], m_side, p, m_stop, m_target, **kw)
            cost_r = self.cost / d
            rows.append({
                "entry_time": bars.index[j], "entry_idx": j, "status": "taken", "side": side,
                "entry_price": p, "stop_price": stop, "target_price": target, "risk": d,
                "outcome": res.outcome, "gross_r": res.r, "cost_r": cost_r, "net_r": res.r - cost_r,
                "mae_r": res.mae_r, "target_anyway": res.target_anyway,
                "direction_right_stop_wrong": res.direction_right_stop_wrong,
                "adverse_before_target_r": res.adverse_before_target_r,
                "flipped_gross_r": flip.r, "flipped_net_r": flip.r - cost_r,
            })
        out = pd.DataFrame(rows)
        if not out.empty:
            out = out.sort_values("entry_time", kind="stable").reset_index(drop=True)
        return out
