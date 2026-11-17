"""Preregistration: freeze a recipe before looking at any result.

A frozen recipe is the recipe itself plus a block with its sha256 fingerprint
and the UTC time of freezing. The fingerprint is computed on a canonical JSON
form of the recipe, so the same content gives the same fingerprint whether you
store it as JSON or YAML.

Rules we learned the hard way:

* the *closing rules* (what makes you declare the idea dead) are written
  before the numbers, and they are part of the fingerprint;
* after the numbers, no tweaks: a new variant is a new recipe with a new
  fingerprint, and it counts as one more trial in the trial log.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Optional

from . import __version__

REQUIRED_KEYS = ("name", "hypothesis", "rules", "closing_rules")
RECOMMENDED_KEYS = ("source", "data", "costs", "controls")


def canonical_json(obj) -> str:
    """Deterministic JSON text: sorted keys, no extra spaces, UTF-8 kept as is."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def fingerprint(recipe: dict) -> str:
    """sha256 of the canonical JSON of the recipe."""
    return hashlib.sha256(canonical_json(recipe).encode("utf-8")).hexdigest()


def check_recipe(recipe: dict) -> list[str]:
    """Problems that block freezing (missing keys, empty closing rules)."""
    problems = [f"missing key: {k}" for k in REQUIRED_KEYS if k not in recipe]
    rules = recipe.get("closing_rules")
    if "closing_rules" in recipe and (not isinstance(rules, list) or not rules or not all(isinstance(x, str) and x.strip() for x in rules)):
        problems.append("closing_rules must be a non-empty list of sentences written before the test")
    return problems


def missing_recommended(recipe: dict) -> list[str]:
    return [k for k in RECOMMENDED_KEYS if k not in recipe]


def _load(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise ImportError("PyYAML is needed for YAML files: pip install pyyaml") from exc
        return yaml.safe_load(text)
    return json.loads(text)


def _dump(obj, path: Path) -> None:
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise ImportError("PyYAML is needed for YAML files: pip install pyyaml") from exc
        path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def freeze_recipe(recipe: dict, path, *, now: Optional[_dt.datetime] = None, overwrite: bool = False) -> dict:
    """Write ``{"recipe": ..., "frozen": {"sha256": ..., "frozen_at_utc": ...}}`` to ``path``.

    Refuses to overwrite an existing file unless ``overwrite=True``: a frozen
    recipe is not edited, it is replaced by a new one with a new name.
    """
    problems = check_recipe(recipe)
    if problems:
        raise ValueError("; ".join(problems))
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} exists: freeze a new version under a new name")
    now = now or _dt.datetime.now(_dt.timezone.utc)
    frozen = {
        "recipe": recipe,
        "frozen": {
            "sha256": fingerprint(recipe),
            "frozen_at_utc": now.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tool": f"goodbye-fuffaguru {__version__}",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    _dump(frozen, path)
    return frozen


def freeze_file(src, dst=None, **kw) -> dict:
    """Freeze a recipe stored in a JSON or YAML file (``dst`` defaults to ``<src>.frozen.json``)."""
    src = Path(src)
    dst = Path(dst) if dst else src.with_name(src.stem + ".frozen.json")
    return freeze_recipe(_load(src), dst, **kw)


def load_frozen(path) -> dict:
    return _load(Path(path))


def verify_frozen(path) -> tuple[bool, str]:
    """Recompute the fingerprint and compare it with the stored one."""
    data = load_frozen(path)
    if not isinstance(data, dict) or "recipe" not in data or "frozen" not in data:
        return False, "not a frozen recipe (missing 'recipe' or 'frozen')"
    stored = data["frozen"].get("sha256", "")
    actual = fingerprint(data["recipe"])
    if stored != actual:
        return False, f"fingerprint mismatch: stored {stored[:12]}..., actual {actual[:12]}... (the recipe was edited)"
    return True, f"ok: sha256 {actual} frozen at {data['frozen'].get('frozen_at_utc', '?')}"


# -------------------------------------------------------------------- trial log


def log_trial(log_path, recipe_sha256: str, test_name: str, result: dict, *, now=None) -> int:
    """Append one line to an append-only JSONL log and return the number of trials so far.

    Count everything: every variant, every instrument, every period you looked
    at. The count is what you need to correct p-values for multiple testing.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    now = now or _dt.datetime.now(_dt.timezone.utc)
    line = {"time_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "recipe_sha256": recipe_sha256,
            "test": test_name, "result": result}
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(canonical_json(line) + "\n")
    return count_trials(log_path)


def count_trials(log_path) -> int:
    log_path = Path(log_path)
    if not log_path.exists():
        return 0
    with log_path.open(encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())
