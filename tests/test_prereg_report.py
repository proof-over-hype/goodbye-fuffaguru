import json

import numpy as np
import pandas as pd
import pytest

from fuffaguru.prereg import (count_trials, fingerprint, freeze_file, freeze_recipe, log_trial, verify_frozen)
from fuffaguru.report import INCONCLUSIVE, NO_EDGE, PASSED, Claims, reality_check

RECIPE = {"name": "test", "hypothesis": "h", "rules": {"a": 1}, "closing_rules": ["dead if mean <= 0"]}


def test_freeze_and_verify(tmp_path):
    out = tmp_path / "r.frozen.json"
    frozen = freeze_recipe(RECIPE, out)
    assert frozen["frozen"]["sha256"] == fingerprint(RECIPE)
    assert verify_frozen(out)[0]
    data = json.loads(out.read_text(encoding="utf-8"))
    data["recipe"]["rules"]["a"] = 2  # edited after freezing
    out.write_text(json.dumps(data), encoding="utf-8")
    ok, msg = verify_frozen(out)
    assert not ok and "mismatch" in msg


def test_freeze_refuses_overwrite_and_missing_closing_rules(tmp_path):
    out = tmp_path / "r.json"
    freeze_recipe(RECIPE, out)
    with pytest.raises(FileExistsError):
        freeze_recipe(RECIPE, out)
    with pytest.raises(ValueError):
        freeze_recipe({**RECIPE, "closing_rules": []}, tmp_path / "x.json")


def test_yaml_and_json_give_same_fingerprint(tmp_path):
    yaml = pytest.importorskip("yaml")
    src = tmp_path / "recipe.yaml"
    src.write_text(yaml.safe_dump(RECIPE), encoding="utf-8")
    frozen = freeze_file(src)
    assert frozen["frozen"]["sha256"] == fingerprint(RECIPE)
    assert verify_frozen(tmp_path / "recipe.frozen.json")[0]


def test_trial_log_counts(tmp_path):
    log = tmp_path / "trials.jsonl"
    for i in range(3):
        n = log_trial(log, "abc", f"t{i}", {"x": i})
    assert n == 3 == count_trials(log)


def fake_results(r, flipped, start="2025-01-01"):
    n = len(r)
    return pd.DataFrame({
        "entry_time": pd.date_range(start, periods=n, freq="6h", tz="UTC"),
        "status": "taken", "side": "long", "outcome": np.where(np.asarray(r) > 0, "target", "stop"),
        "gross_r": r, "cost_r": 0.0, "net_r": r, "flipped_net_r": flipped,
        "direction_right_stop_wrong": False, "adverse_before_target_r": np.nan,
    })


def test_verdict_inconclusive_with_few_trades():
    rc = reality_check(fake_results([1.0] * 10, [-1.0] * 10), n_sims=200)
    assert rc.verdict == INCONCLUSIVE


def test_verdict_no_edge_on_noise():
    rng = np.random.default_rng(5)
    r = rng.choice([1.0, -1.0], 300)
    rc = reality_check(fake_results(r - 0.05, -r - 0.05), n_sims=500)
    assert rc.verdict == NO_EDGE and rc.reasons


def test_verdict_passed_is_never_called_proof():
    rc = reality_check(fake_results([1.0] * 80 + [-1.0] * 20, [-1.0] * 80 + [1.0] * 20), n_sims=500,
                       claims=Claims(win_rate=0.95, win_rate_basis="days"))
    assert rc.verdict == PASSED
    md = rc.to_markdown()
    assert "NOT A PROOF" in md and "not financial advice" in md
    assert any("claimed win rate" in w for w in rc.warnings)


def test_multiple_testing_can_flip_the_verdict():
    rng = np.random.default_rng(11)
    r = rng.choice([1.0, -1.0], 200, p=[0.58, 0.42])
    base = fake_results(r, -r)
    one = reality_check(base, n_sims=2000)
    many = reality_check(base, n_sims=2000, n_trials=200)
    assert many.adjusted_p[0] >= one.adjusted_p[0]
