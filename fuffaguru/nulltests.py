"""Null tests: does the result beat what chance gives in the same conditions?

Every test returns a ``NullResult`` with the observed statistic, the
distribution of the same statistic under the null, and a one-sided p-value
(probability of doing at least as well by chance). The p-values use the
"+1" correction, so they are never exactly zero.

The two most useful nulls in our experience:

* **random direction at the same instants**: same entry times, same stop and
  target distances, but long or short decided by a coin. If the trader's
  direction call has no value, the real result sits in the middle of this
  distribution. Costs are identical, so they do not matter for the comparison.
* **fake levels**: the same recipe run on levels shifted by a random amount.
  If the "special" zones of the trader are no better than arbitrary prices,
  the place does not matter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

import numpy as np


@dataclass
class NullResult:
    name: str
    observed: float
    null: np.ndarray = field(repr=False)
    p_value: float
    n: int
    description: str = ""

    @property
    def null_mean(self) -> float:
        return float(np.mean(self.null)) if self.null.size else float("nan")

    def null_quantile(self, q: float) -> float:
        return float(np.quantile(self.null, q)) if self.null.size else float("nan")

    def passed(self, alpha: float = 0.05) -> bool:
        return self.p_value <= alpha

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "observed": self.observed,
            "null_mean": self.null_mean,
            "null_p05": self.null_quantile(0.05),
            "null_p95": self.null_quantile(0.95),
            "p_value": self.p_value,
            "n": self.n,
            "sims": int(self.null.size),
            "description": self.description,
        }


def p_value_greater(observed: float, null: Sequence[float]) -> float:
    """One-sided p-value: share of null draws at least as good as the observed value."""
    null = np.asarray(null, dtype=float)
    return float((1 + np.sum(null >= observed - 1e-12)) / (null.size + 1))


# ------------------------------------------------------------- random direction


def random_direction_test(
    r: Sequence[float],
    r_flipped: Sequence[float],
    n_sims: int = 10_000,
    seed: Optional[int] = 0,
    stat: Callable[[np.ndarray], float] = np.mean,
) -> NullResult:
    """Coin-flip the direction of every trade at the same instant.

    ``r`` are the results of the real trades, ``r_flipped`` the results of the
    mirrored trades (same entry, same stop and target distances, opposite side).
    Use net results in both if you want the null to include costs.
    """
    a = np.asarray(r, dtype=float)
    b = np.asarray(r_flipped, dtype=float)
    keep = ~(np.isnan(a) | np.isnan(b))
    a, b = a[keep], b[keep]
    rng = np.random.default_rng(seed)
    if a.size == 0:
        return NullResult("random direction, same instants", float("nan"), np.array([]), 1.0, 0)
    pick = rng.random((n_sims, a.size)) < 0.5
    sims = np.where(pick, a, b)
    null = np.apply_along_axis(stat, 1, sims) if stat is not np.mean else sims.mean(axis=1)
    obs = float(stat(a))
    return NullResult(
        name="random direction, same instants",
        observed=obs,
        null=null,
        p_value=p_value_greater(obs, null),
        n=int(a.size),
        description="Same entry times and stop/target distances; long or short by coin flip.",
    )


def same_instant_baselines(r: Sequence[float], r_flipped: Sequence[float], sides: Sequence[str]) -> dict:
    """Mean R of 'always long' and 'always short' at the same instants.

    In a market that went up for the whole period, a recipe can look good just
    because most of its trades were long: compare it with 'always long'.
    """
    a = np.asarray(r, dtype=float)
    b = np.asarray(r_flipped, dtype=float)
    is_long = np.asarray([s == "long" for s in sides])
    r_long = np.where(is_long, a, b)
    r_short = np.where(is_long, b, a)
    return {
        "always_long": float(np.nanmean(r_long)) if r_long.size else float("nan"),
        "always_short": float(np.nanmean(r_short)) if r_short.size else float("nan"),
        "share_long": float(is_long.mean()) if is_long.size else float("nan"),
    }


# ------------------------------------------------------------------ fake levels


def shift_levels(
    levels: Sequence[float],
    scale: Sequence[float] | float,
    rng: np.random.Generator,
    min_shift: float = 0.5,
    max_shift: float = 3.0,
) -> np.ndarray:
    """Move every level up or down by U(min_shift, max_shift) times ``scale`` (e.g. ATR)."""
    lv = np.asarray(levels, dtype=float)
    sc = np.broadcast_to(np.asarray(scale, dtype=float), lv.shape)
    size = rng.uniform(min_shift, max_shift, lv.shape)
    sign = np.where(rng.random(lv.shape) < 0.5, -1.0, 1.0)
    return lv + sign * size * sc


def fake_levels_test(
    evaluate: Callable[[np.ndarray], float],
    levels: Sequence[float],
    scale: Sequence[float] | float,
    n_sims: int = 200,
    seed: Optional[int] = 0,
    min_shift: float = 0.5,
    max_shift: float = 3.0,
    name: str = "fake levels (shifted)",
) -> NullResult:
    """Run ``evaluate`` on the real levels and on ``n_sims`` sets of shifted levels.

    ``evaluate(levels) -> float`` runs your recipe with the given level prices
    and returns the statistic to compare (mean net R, share of targets hit...).
    Everything else in the recipe must stay identical.
    """
    rng = np.random.default_rng(seed)
    lv = np.asarray(levels, dtype=float)
    obs = float(evaluate(lv))
    null = np.array([evaluate(shift_levels(lv, scale, rng, min_shift, max_shift)) for _ in range(n_sims)])
    null = null[~np.isnan(null)]
    return NullResult(
        name=name,
        observed=obs,
        null=null,
        p_value=p_value_greater(obs, null),
        n=int(lv.size),
        description=f"Same recipe on levels moved by {min_shift}-{max_shift} x scale, up or down at random.",
    )


# -------------------------------------------------------------------- bootstrap


def bootstrap_mean_ci(r: Sequence[float], n_boot: int = 10_000, ci: float = 0.95, seed: Optional[int] = 0):
    """Percentile bootstrap interval of the mean."""
    a = np.asarray(r, dtype=float)
    a = a[~np.isnan(a)]
    if a.size == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = a[rng.integers(0, a.size, (n_boot, a.size))].mean(axis=1)
    lo, hi = np.quantile(means, [(1 - ci) / 2, 1 - (1 - ci) / 2])
    return float(lo), float(hi)


def bootstrap_test(r: Sequence[float], n_boot: int = 10_000, seed: Optional[int] = 0) -> NullResult:
    """One-sided test of 'mean R > 0' with a bootstrap of the re-centred sample."""
    a = np.asarray(r, dtype=float)
    a = a[~np.isnan(a)]
    rng = np.random.default_rng(seed)
    if a.size == 0:
        return NullResult("bootstrap, mean > 0", float("nan"), np.array([]), 1.0, 0)
    centred = a - a.mean()
    null = centred[rng.integers(0, a.size, (n_boot, a.size))].mean(axis=1)
    obs = float(a.mean())
    return NullResult(
        name="bootstrap, mean > 0",
        observed=obs,
        null=null,
        p_value=p_value_greater(obs, null),
        n=int(a.size),
        description="Resampling of the trades after removing their mean.",
    )


# ------------------------------------------------------------------------ costs


def cost_in_r(cost_price: float, risk_price: float) -> float:
    """Round-trip cost (spread + commission + slippage) as a fraction of the risk."""
    if risk_price <= 0:
        raise ValueError("risk must be positive")
    return cost_price / risk_price


def breakeven_win_rate(reward_r: float, cost_r: float = 0.0) -> float:
    """Win rate needed to break even with a fixed reward of ``reward_r`` R and a cost of ``cost_r`` R.

    A win pays ``reward_r - cost_r``, a loss costs ``1 + cost_r``:
    p = (1 + cost_r) / (reward_r + 1). With 1:1 and a cost of 0.10 R you need 55%.
    """
    return (1.0 + cost_r) / (reward_r + 1.0)


# ------------------------------------------------------------ multiple testing


def sidak_adjust(p_value: float, n_trials: int) -> float:
    """Chance that at least one of ``n_trials`` independent tries looks this good by luck."""
    n_trials = max(1, int(n_trials))
    return float(1.0 - (1.0 - p_value) ** n_trials)
