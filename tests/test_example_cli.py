import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from fuffaguru.cli import main
from fuffaguru.report import NO_EDGE
from fuffaguru.synthetic import random_walk_bars

ROOT = Path(__file__).resolve().parents[1]


def load_example():
    spec = importlib.util.spec_from_file_location("run_example", ROOT / "examples" / "synthetic_guru" / "run_example.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_synthetic_guru_looks_good_in_sample_but_has_no_edge(tmp_path):
    out = load_example().run(tmp_path, quick=True, verbose=False)
    assert out["dev_summary"]["mean"] > 0.1          # the guru's backtest looks great...
    assert out["verdict"] == NO_EDGE                  # ...but it does not survive the checks
    assert out["confirmation"]["mean"] < 0.05
    assert (tmp_path / "REALITY_CHECK.md").exists() and (tmp_path / "recipe.frozen.json").exists()


def test_cli_verify_and_freeze(tmp_path):
    bars = random_walk_bars(3000, freq="1min", seed=3)
    bars.reset_index().to_csv(tmp_path / "bars.csv", index=False)
    rng = np.random.default_rng(0)
    rows = []
    for i, j in enumerate(rng.choice(np.arange(10, 2800), 40, replace=False)):
        t, price = bars.index[j], float(bars["close"].iloc[j])
        side = "long" if i % 2 else "short"
        sign = 1 if side == "long" else -1
        rows.append({"trade_id": f"t{i}", "status": "taken", "instrument": "SYN", "side": side,
                     "entry_time": t.isoformat(), "entry_price": price, "stop_price": price - sign * 3,
                     "target_price": price + sign * 6})
    pd.DataFrame(rows).to_csv(tmp_path / "trades.csv", index=False)
    rc = main(["verify", str(tmp_path / "trades.csv"), str(tmp_path / "bars.csv"), "--out",
               str(tmp_path / "v.csv"), "--report", str(tmp_path / "r.md"), "--sims", "300", "--cost", "0.2"])
    assert rc == 0 and (tmp_path / "r.md").read_text(encoding="utf-8").startswith("# Reality Check")
    recipe = tmp_path / "recipe.json"
    recipe.write_text('{"name":"x","hypothesis":"h","rules":{},"closing_rules":["dead if <= 0"]}', encoding="utf-8")
    assert main(["freeze", str(recipe)]) == 0
    assert main(["check-freeze", str(tmp_path / "recipe.frozen.json")]) == 0


def test_cli_follow_and_status(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "follow", "https://www.tiktok.com/@someone"]) == 0
    assert main(["--root", str(tmp_path), "status"]) == 0
    out = capsys.readouterr().out
    assert "tiktok:someone" in out
