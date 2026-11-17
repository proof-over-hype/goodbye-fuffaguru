import numpy as np
import pandas as pd
import pytest

from fuffaguru.metrics import expectancy_by_period, summarize_r, win_rate_by_days
from fuffaguru.nulltests import (bootstrap_mean_ci, bootstrap_test, breakeven_win_rate, fake_levels_test,
                                 p_value_greater, random_direction_test, same_instant_baselines, shift_levels,
                                 sidak_adjust)


def test_p_value_has_plus_one_correction():
    assert p_value_greater(10, [0, 1, 2]) == pytest.approx(1 / 4)
    assert p_value_greater(-10, [0, 1, 2]) == 1.0


def test_random_direction_detects_a_real_direction_skill():
    r = np.ones(60)
    res = random_direction_test(r, -np.ones(60), n_sims=2000, seed=1)
    assert res.p_value < 0.001


def test_random_direction_gives_no_edge_when_direction_does_not_matter():
    rng = np.random.default_rng(0)
    r = rng.choice([1.0, -1.0], 200)
    res = random_direction_test(r, r, n_sims=500)
    assert res.p_value == 1.0  # every coin flip gives the same result


def test_baselines():
    b = same_instant_baselines([1, -1], [-1, 1], ["long", "short"])
    assert b["always_long"] == 1.0 and b["always_short"] == -1.0


def test_shift_levels_stays_within_bounds():
    rng = np.random.default_rng(0)
    lv = np.full(1000, 100.0)
    moved = shift_levels(lv, 2.0, rng, 0.5, 3.0)
    d = np.abs(moved - lv)
    assert d.min() >= 1.0 - 1e-9 and d.max() <= 6.0 + 1e-9
    assert (moved > lv).any() and (moved < lv).any()


def test_fake_levels_constant_recipe_is_not_better_than_fake():
    res = fake_levels_test(lambda p: 0.1, [1, 2, 3], 1.0, n_sims=50)
    assert res.p_value == 1.0


def test_bootstrap():
    rng = np.random.default_rng(3)
    r = rng.normal(0.5, 1, 400)
    lo, hi = bootstrap_mean_ci(r)
    assert lo < r.mean() < hi
    assert bootstrap_test(r).p_value < 0.01
    assert bootstrap_test(rng.normal(0, 1, 400) - 0.2).p_value > 0.5


def test_costs_and_multiple_testing():
    assert breakeven_win_rate(1.0, 0.10) == pytest.approx(0.55)
    assert breakeven_win_rate(2.0) == pytest.approx(1 / 3)
    assert sidak_adjust(0.01, 1) == pytest.approx(0.01)
    assert sidak_adjust(0.01, 48) == pytest.approx(1 - 0.99 ** 48)


def test_days_versus_trades():
    # each day: one +1.5 R win and one -1 R loss -> 50% of trades win, 100% of days positive
    times = pd.to_datetime(["2025-01-06 10:00", "2025-01-06 11:00", "2025-01-07 10:00", "2025-01-07 11:00"], utc=True)
    out = win_rate_by_days(times, [1.5, -1, 1.5, -1])
    assert out["trade_win_rate"] == 0.5 and out["positive_day_rate"] == 1.0


def test_summary_and_periods():
    s = summarize_r([1, -1, 0, 2])
    assert s["n"] == 4 and s["win_rate"] == 0.5 and s["breakeven_rate"] == 0.25
    assert s["max_drawdown"] == pytest.approx(1.0)
    times = pd.date_range("2025-01-01", periods=9, freq="D", tz="UTC")
    per = expectancy_by_period(times, [2, 2, 2, 1, 1, 1, 0, 0, 0])
    assert list(per["mean_r"]) == [2, 1, 0]
