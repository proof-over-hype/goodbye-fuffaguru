import io

import numpy as np
import pandas as pd
import pytest

from fuffaguru.trades import (mirror, normalise_bars, read_trades, simulate_path, validate_trades,
                              verify_trades)


def bars_from(rows, start="2025-01-06 10:00", freq="1min"):
    idx = pd.date_range(start, periods=len(rows), freq=freq, tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def test_long_hits_target():
    r = simulate_path([101, 103], [99.5, 100.5], [100.5, 102.5], "long", 100, 99, 102)
    assert r.outcome == "target" and r.r == pytest.approx(2.0)


def test_short_hits_stop_then_target_is_right_direction_wrong_stop():
    # short at 100, stop 101: first bar spikes to 101.2 (stop), later price falls to 98 (target)
    r = simulate_path([101.2, 100.0, 99.0], [99.8, 98.9, 97.9], [100.5, 99.2, 98.1], "short", 100, 101, 98)
    assert r.outcome == "stop" and r.r == -1
    assert r.target_anyway and r.direction_right_stop_wrong
    assert r.adverse_before_target_r == pytest.approx(1.2)


def test_same_bar_is_resolved_against_the_trade_by_default():
    args = ([103], [98.5], [100], "long", 100, 99, 102)
    assert simulate_path(*args).outcome == "stop"
    assert simulate_path(*args, same_bar="target_first").outcome == "target"


def test_breakeven_rule():
    # +0.5R reached, then price returns to entry: breakeven, not a loss
    r = simulate_path([100.6, 100.2, 100.1], [99.9, 99.95, 99.5], [100.5, 100.0, 99.6], "long", 100, 99, 101,
                      breakeven_at_r=0.5)
    assert r.outcome == "breakeven" and r.r == 0.0


def test_timeout_marks_to_last_close():
    r = simulate_path([100.4, 100.5], [99.6, 99.7], [100.2, 100.3], "long", 100, 99, 102)
    assert r.outcome == "timeout" and r.r == pytest.approx(0.3)


def test_first_bar_stop_only_ignores_target_in_entry_bar():
    r = simulate_path([102.5, 100.2], [99.5, 99.8], [100, 100], "long", 100, 99, 102, first_bar_stop_only=True)
    assert r.outcome == "timeout"


def test_mirror():
    side, stop, target = mirror("long", 100, 99, 102)
    assert (side, stop, target) == ("short", 101, 98)


CSV = """trade_id,status,instrument,side,entry_time,entry_price,stop_price,target_price
t1,taken,X,long,2025-01-06T10:00:30Z,100,99,102
t2,skipped,X,short,2025-01-06T10:01:10Z,101,102,99
t3,taken,X,long,2025-01-06T10:02:00Z,100,101,102
"""


def test_validate_flags_wrong_side_stop():
    df = read_trades(io.StringIO(CSV))
    problems = validate_trades(df)
    assert any("t3" in p and "wrong side" in p for p in problems)
    assert not any(p.startswith("t1") for p in problems)


def test_verify_trades_end_to_end():
    bars = bars_from([[100, 100.4, 99.8, 100.2], [100.2, 101.0, 100.1, 100.9], [100.9, 102.2, 100.8, 102.0],
                      [102, 102.1, 101.5, 101.8]])
    df = read_trades(io.StringIO(CSV)).iloc[:2]
    res = verify_trades(df, bars, cost=0.1)
    t1 = res.set_index("trade_id").loc["t1"]
    assert t1["outcome"] == "target" and t1["entry_traded"]
    assert t1["net_r"] == pytest.approx(2.0 - 0.1)
    assert t1["flipped_outcome"] == "stop"
    t2 = res.set_index("trade_id").loc["t2"]
    assert t2["status"] == "skipped"


def test_normalise_bars_accepts_naive_times():
    df = pd.DataFrame({"time": ["2025-01-06 10:00", "2025-01-06 10:01"], "open": [1, 2], "high": [2, 3],
                       "low": [0.5, 1.5], "close": [2, 2.5]})
    out = normalise_bars(df)
    assert str(out.index.tz) == "UTC" and len(out) == 2


def test_no_data_when_entry_outside_bars():
    bars = bars_from([[100, 101, 99, 100]])
    df = read_trades(io.StringIO(CSV.replace("2025-01-06T10:00:30Z", "2024-01-01T00:00:00Z"))).iloc[:1]
    assert verify_trades(df, bars)["outcome"].iloc[0] == "no_data"
