"""Trade schema and verification of trades on OHLC bars supplied by the user.

A "trade" here is anything a trader shows or describes:

* ``taken``   an order the trader actually placed (seen on screen or in a journal);
* ``skipped`` a setup the trader looked at and passed on;
* ``drawn``   a position only drawn on the chart (a risk/reward box, an arrow);
* ``told``    a result only told after the fact ("I took this one this morning").

Only ``taken`` trades form the sample that says something about results. The
other statuses are kept because they tell you whether the trader's own filters
help (do skipped setups lose?) and how much the shown material is selected
(told trades are almost always winners).

Verification replays each trade on bars that *you* provide (1-minute bars or
finer are strongly recommended). Inside a single bar the order of the high and
the low is unknown, so every ambiguity is resolved against the trade by
default. See ``simulate_path`` for the exact rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Union

import numpy as np
import pandas as pd

#: Columns of the trade CSV, with a one-line description each.
TRADE_COLUMNS: dict[str, str] = {
    "trade_id": "Unique id of the row (any string).",
    "source": "Where it comes from: a neutral label such as 'video-07' or 'live-3'.",
    "source_time": "Position inside the source (hh:mm:ss) where the trade is shown or said.",
    "status": "taken | skipped | drawn | told",
    "instrument": "Symbol, as named in your bar files (e.g. XAUUSD, NQ).",
    "side": "long | short",
    "entry_time": "ISO-8601 entry time, preferably UTC (e.g. 2025-03-04T14:31:00Z).",
    "entry_price": "Entry price.",
    "stop_price": "Initial stop price.",
    "target_price": "Target price (optional; if empty a fixed target in R can be used).",
    "claimed_result_r": "Result in R claimed by the trader (optional).",
    "confidence": "high | medium | low: how sure you are of the reading.",
    "notes": "Free text. Keep 'said', 'seen' and 'inferred' apart.",
}

REQUIRED_COLUMNS = ("trade_id", "status", "side", "entry_time", "entry_price", "stop_price")
STATUSES = ("taken", "skipped", "drawn", "told")
SIDES = ("long", "short")
NUMERIC_COLUMNS = ("entry_price", "stop_price", "target_price", "claimed_result_r")
BAR_COLUMNS = ("open", "high", "low", "close")

BarsLike = Union[pd.DataFrame, Mapping[str, pd.DataFrame]]


# --------------------------------------------------------------------------- I/O


def read_trades(path) -> pd.DataFrame:
    """Read a trade CSV and normalise types (times to UTC, prices to float)."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return normalise_trades(df)


def normalise_trades(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with all schema columns present and typed."""
    out = df.copy()
    for col in TRADE_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    for col in ("status", "side", "confidence"):
        out[col] = out[col].astype(str).str.strip().str.lower()
    for col in NUMERIC_COLUMNS:
        out[col] = pd.to_numeric(out[col].replace("", np.nan), errors="coerce")
    out["entry_time"] = pd.to_datetime(out["entry_time"].replace("", None), utc=True, errors="coerce")
    out["trade_id"] = out["trade_id"].astype(str)
    return out


def validate_trades(df: pd.DataFrame) -> list[str]:
    """Return a list of human-readable problems (empty list = looks fine)."""
    problems: list[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return [f"missing required columns: {', '.join(missing)}"]
    dup = df["trade_id"][df["trade_id"].duplicated()].tolist()
    if dup:
        problems.append(f"duplicated trade_id: {', '.join(map(str, dup))}")
    for _, row in df.iterrows():
        tid = row["trade_id"]
        if row["status"] not in STATUSES:
            problems.append(f"{tid}: status must be one of {STATUSES}, got {row['status']!r}")
        if row["side"] not in SIDES:
            problems.append(f"{tid}: side must be long or short, got {row['side']!r}")
            continue
        if pd.isna(row["entry_time"]):
            problems.append(f"{tid}: entry_time missing or not a valid date/time")
        entry, stop, target = row["entry_price"], row["stop_price"], row.get("target_price", np.nan)
        if pd.isna(entry) or pd.isna(stop):
            problems.append(f"{tid}: entry_price and stop_price are required")
            continue
        sign = 1.0 if row["side"] == "long" else -1.0
        if sign * (entry - stop) <= 0:
            problems.append(f"{tid}: stop is on the wrong side of the entry for a {row['side']}")
        if not pd.isna(target) and sign * (target - entry) <= 0:
            problems.append(f"{tid}: target is on the wrong side of the entry for a {row['side']}")
    return problems


def read_bars(path, time_col: str = "time", tz: str = "UTC") -> pd.DataFrame:
    """Read OHLC bars from CSV. Columns: time, open, high, low, close (volume optional).

    ``time`` is the bar *open* time. Naive times are interpreted in ``tz``.
    """
    df = pd.read_csv(path)
    return normalise_bars(df, time_col=time_col, tz=tz)


def normalise_bars(df: pd.DataFrame, time_col: str = "time", tz: str = "UTC") -> pd.DataFrame:
    """Return bars indexed by a sorted UTC DatetimeIndex with float OHLC columns."""
    out = df.copy()
    if time_col in out.columns:
        times = pd.to_datetime(out[time_col], errors="raise")
        out = out.drop(columns=[time_col])
    else:
        times = pd.to_datetime(out.index)
    times = pd.DatetimeIndex(times)
    times = times.tz_localize(tz) if times.tz is None else times
    out.index = times.tz_convert("UTC")
    out.index.name = "time"
    missing = [c for c in BAR_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(f"bars are missing columns: {', '.join(missing)}")
    for c in BAR_COLUMNS:
        out[c] = out[c].astype(float)
    return out.sort_index()


def validate_bars(bars: pd.DataFrame) -> list[str]:
    """Basic sanity checks on OHLC bars."""
    problems = []
    if bars.index.has_duplicates:
        problems.append("duplicated bar times")
    bad_high = bars["high"] < bars[["open", "close"]].max(axis=1)
    bad_low = bars["low"] > bars[["open", "close"]].min(axis=1)
    if bad_high.any():
        problems.append(f"{int(bad_high.sum())} bars with high below open/close")
    if bad_low.any():
        problems.append(f"{int(bad_low.sum())} bars with low above open/close")
    return problems


# --------------------------------------------------------------------- simulation


@dataclass
class PathResult:
    """Outcome of one trade replayed on bars.

    outcome:  'target', 'stop', 'breakeven', 'timeout' or 'no_data'
    r:        gross result in R (risk = |entry - stop|), before costs
    exit_offset: index (relative to the first bar checked) of the exit bar
    mae_r / mfe_r: max adverse / favourable excursion in R up to the exit bar
    target_anyway: the target was touched within the horizon *ignoring the stop*
    bars_to_target_anyway: offset of that bar
    adverse_before_target_r: worst adverse excursion (R) in the bars before the
        target bar, ignoring the stop: how wide the stop had to be
    """

    outcome: str
    r: float
    exit_offset: Optional[int]
    mae_r: float
    mfe_r: float
    target_anyway: bool
    bars_to_target_anyway: Optional[int]
    adverse_before_target_r: Optional[float]

    @property
    def direction_right_stop_wrong(self) -> bool:
        """Stopped out, yet the target was reached later within the horizon."""
        return self.outcome == "stop" and self.target_anyway


def _first(mask: np.ndarray, start: int = 0) -> Optional[int]:
    idx = np.flatnonzero(mask[start:])
    return int(start + idx[0]) if idx.size else None


def simulate_path(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    side: str,
    entry: float,
    stop: float,
    target: Optional[float],
    *,
    breakeven_at_r: Optional[float] = None,
    same_bar: str = "stop_first",
    first_bar_stop_only: bool = False,
) -> PathResult:
    """Replay a trade on the bars after the entry.

    ``high``, ``low`` and ``close`` must already be cut to the bars to check,
    in time order (the caller decides the horizon).

    Rules, all conservative:

    * a stop or target counts as hit when the price touches it (equal counts);
    * if stop and target are touched in the same bar, ``same_bar='stop_first'``
      (default) counts a loss; ``'target_first'`` counts a win;
    * ``breakeven_at_r``: once the favourable excursion reaches this many R the
      stop moves to the entry price, from the *next* bar on; a stop touched in
      the same bar as the trigger is a full loss;
    * ``first_bar_stop_only``: the first bar is the entry bar, so only the stop
      is checked there (we cannot know if the target came after the entry);
    * no exit within the bars: 'timeout', marked to the last close.
    """
    if side not in SIDES:
        raise ValueError("side must be 'long' or 'short'")
    risk = abs(entry - stop)
    if not risk > 0:
        raise ValueError("entry and stop must differ")
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    n = len(high)
    if n == 0:
        return PathResult("no_data", float("nan"), None, float("nan"), float("nan"), False, None, None)

    sign = 1.0 if side == "long" else -1.0
    if sign * (entry - stop) <= 0:
        raise ValueError("stop is on the wrong side of the entry")
    if side == "long":
        adverse = (entry - low) / risk
        favour = (high - entry) / risk
    else:
        adverse = (high - entry) / risk
        favour = (entry - low) / risk

    reward = None if target is None or np.isnan(target) else sign * (target - entry) / risk
    if reward is not None and reward <= 0:
        raise ValueError("target is on the wrong side of the entry")

    stop_hit = adverse >= 1.0
    tgt_hit = favour >= reward if reward is not None else np.zeros(n, dtype=bool)
    be_on = breakeven_at_r is not None and (reward is None or breakeven_at_r < reward)
    be_hit = favour >= breakeven_at_r if be_on else np.zeros(n, dtype=bool)
    if first_bar_stop_only:
        tgt_hit = tgt_hit.copy()
        be_hit = be_hit.copy()
        tgt_hit[0] = False
        be_hit[0] = False

    i_tgt_any = _first(tgt_hit)
    adverse_before = None
    if i_tgt_any is not None:
        adverse_before = float(max(0.0, adverse[:i_tgt_any].max())) if i_tgt_any > 0 else 0.0

    def finish(outcome: str, r: float, i: int) -> PathResult:
        return PathResult(
            outcome=outcome,
            r=float(r),
            exit_offset=i,
            mae_r=float(max(0.0, adverse[: i + 1].max())),
            mfe_r=float(max(0.0, favour[: i + 1].max())),
            target_anyway=i_tgt_any is not None,
            bars_to_target_anyway=i_tgt_any,
            adverse_before_target_r=adverse_before,
        )

    i_stop = _first(stop_hit)
    i_tgt = i_tgt_any
    i_be = _first(be_hit)
    big = n + 1
    s, t, b = (i_stop if i_stop is not None else big, i_tgt if i_tgt is not None else big,
               i_be if i_be is not None else big)

    # Phase 1: original stop.
    if s < big and s <= b and (s < t or (s == t and same_bar == "stop_first")):
        return finish("stop", -1.0, s)
    if t < big and t <= b:
        return finish("target", reward, t)
    if b < big:
        # Phase 2: stop at entry from the bar after the trigger.
        be_stop = adverse >= 0.0
        j_be = _first(be_stop, b + 1)
        j_t = _first(tgt_hit, b + 1) if t > b else t
        jb = j_be if j_be is not None else big
        jt = j_t if j_t is not None else big
        if jt < big and (jt < jb or (jt == jb and same_bar == "target_first")):
            return finish("target", reward, jt)
        if jb < big:
            return finish("breakeven", 0.0, jb)
    last = n - 1
    return finish("timeout", sign * (close[last] - entry) / risk, last)


def mirror(side: str, entry: float, stop: float, target: Optional[float]):
    """The same geometry in the opposite direction (used by the random-direction null)."""
    other = "short" if side == "long" else "long"
    m_stop = 2 * entry - stop
    m_target = None if target is None or np.isnan(target) else 2 * entry - target
    return other, m_stop, m_target


def locate_bar(index: pd.DatetimeIndex, t: pd.Timestamp) -> int:
    """Index of the bar containing time ``t`` (bars are labelled by open time); -1 if before."""
    return int(index.searchsorted(t, side="right")) - 1


# ------------------------------------------------------------------- verification


def _bars_for(bars: BarsLike, instrument: str) -> Optional[pd.DataFrame]:
    if isinstance(bars, pd.DataFrame):
        return bars
    return bars.get(instrument)


def verify_trades(
    trades: pd.DataFrame,
    bars: BarsLike,
    *,
    max_minutes: float = 24 * 60,
    target_r: Optional[float] = None,
    cost: float = 0.0,
    entry_bar: str = "stop_only",
    same_bar: str = "stop_first",
    price_tolerance: float = 0.0,
    breakeven_at_r: Optional[float] = None,
) -> pd.DataFrame:
    """Replay every trade on the bars and return one row of results per trade.

    Parameters
    ----------
    trades: DataFrame in the trade schema (see ``read_trades``).
    bars: one DataFrame of bars, or a mapping ``instrument -> bars``.
    max_minutes: horizon after the entry; no exit by then = 'timeout'.
    target_r: fixed target in R used when a row has no ``target_price``.
    cost: round-trip cost in *price units* (spread + commission + slippage).
    entry_bar: 'stop_only' (default, conservative) checks only the stop in the
        bar containing the entry; 'skip' starts from the next bar; 'full' checks
        stop and target in the entry bar too. If you record entries taken at the
        close of a candle, write the close time as entry_time.
    price_tolerance: allowed distance when checking that the entry price was
        actually traded in the entry bar (e.g. half the spread).
    breakeven_at_r: optional breakeven rule (see ``simulate_path``).
    """
    if entry_bar not in ("stop_only", "skip", "full"):
        raise ValueError("entry_bar must be 'stop_only', 'skip' or 'full'")
    trades = normalise_trades(trades) if trades["entry_time"].dtype == object else trades
    rows = []
    horizon = pd.Timedelta(minutes=max_minutes)
    for _, tr in trades.iterrows():
        base = {
            "trade_id": tr["trade_id"],
            "status": tr["status"],
            "instrument": tr.get("instrument", ""),
            "side": tr["side"],
            "entry_time": tr["entry_time"],
            "entry_price": tr["entry_price"],
            "stop_price": tr["stop_price"],
            "claimed_result_r": tr.get("claimed_result_r", np.nan),
            "confidence": tr.get("confidence", ""),
        }
        b = _bars_for(bars, tr.get("instrument", ""))
        entry, stop = float(tr["entry_price"]), float(tr["stop_price"])
        risk = abs(entry - stop)
        target = tr.get("target_price", np.nan)
        if (target is None or pd.isna(target)) and target_r is not None:
            target = entry + (target_r * risk if tr["side"] == "long" else -target_r * risk)
        target = None if target is None or pd.isna(target) else float(target)
        base.update(target_price=target, risk=risk,
                    reward_r=(abs(target - entry) / risk if target is not None else np.nan))
        if b is None or pd.isna(tr["entry_time"]):
            rows.append({**base, "outcome": "no_data"})
            continue
        i0 = locate_bar(b.index, tr["entry_time"])
        if i0 < 0 or i0 >= len(b):
            rows.append({**base, "outcome": "no_data"})
            continue
        bar0 = b.iloc[i0]
        traded = bool(bar0["low"] - price_tolerance <= entry <= bar0["high"] + price_tolerance)
        start = i0 + 1 if entry_bar == "skip" else i0
        end = int(b.index.searchsorted(tr["entry_time"] + horizon, side="right"))
        window = b.iloc[start:end]
        h, lo, c = (window[col].to_numpy() for col in ("high", "low", "close"))
        kw = dict(breakeven_at_r=breakeven_at_r, same_bar=same_bar,
                  first_bar_stop_only=(entry_bar == "stop_only"))
        res = simulate_path(h, lo, c, tr["side"], entry, stop, target, **kw)
        m_side, m_stop, m_target = mirror(tr["side"], entry, stop, target)
        flip = simulate_path(h, lo, c, m_side, entry, m_stop, m_target, **kw)
        cost_r = cost / risk if risk > 0 else np.nan

        def when(off):
            return window.index[off] if off is not None else pd.NaT

        rows.append({
            **base,
            "entry_traded": traded,
            "outcome": res.outcome,
            "exit_time": when(res.exit_offset),
            "gross_r": res.r,
            "cost_r": cost_r,
            "net_r": res.r - cost_r,
            "mae_r": res.mae_r,
            "mfe_r": res.mfe_r,
            "target_anyway": res.target_anyway,
            "target_anyway_time": when(res.bars_to_target_anyway),
            "adverse_before_target_r": res.adverse_before_target_r,
            "direction_right_stop_wrong": res.direction_right_stop_wrong,
            "flipped_outcome": flip.outcome,
            "flipped_gross_r": flip.r,
            "flipped_net_r": flip.r - cost_r,
        })
    return pd.DataFrame(rows)
