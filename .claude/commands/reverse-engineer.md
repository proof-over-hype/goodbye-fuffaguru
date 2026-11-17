---
description: From a trader's transcripts derive the recipe, preregister it, and test it against chance
argument-hint: <profile key or handle>
---

Reverse-engineer the method of: $ARGUMENTS

PY = `.venv\Scripts\python` on Windows, `.venv/bin/python` elsewhere.
Work folder: `data/<platform>/<handle>/analysis/` (create it).

1. **Collect the text**: transcripts in `history/*/transcript/*.md` and `live/*/transcript.md`, plus any
   `report.md` and `trades.csv` of analysed lives.
2. **Rules**: apply `fuffaguru/prompts/extract_rules.md`. Write `rules.md`: layers, sources with timestamps,
   tags (said / seen / inferred / ours), vague rules, contradictions, what is "in the course".
   Compare with the live trades: does the trader do what they teach?
3. **Recipe**: apply `fuffaguru/prompts/rules_to_recipe.md`. Write `recipe.json` with rules, thresholds (fixed
   from charts, never from results), data periods (development, a LATER confirmation period, a related
   instrument), costs, controls, at most two variants, and closing rules. Add the A1-A9 table.
4. **Freeze BEFORE any number**: `PY -m fuffaguru freeze recipe.json` -> `recipe.frozen.json`. Show the user the
   fingerprint. From now on the recipe does not change.
5. **Implement and test** in a script `recipe_test.py` in the work folder: build on `fuffaguru.recipes`,
   `fuffaguru.trades.simulate_path` and `fuffaguru.nulltests` (random direction at the same instants, fake levels,
   bootstrap), with the costs of the recipe. Log every run with `fuffaguru.prereg.log_trial` into `trials.jsonl`.
   Run development first, then the confirmation period and the related instrument, exactly as frozen.
6. **Critic**: give the frozen recipe, the script and the results to the `stats-critic` sub-agent before
   concluding. Fix only bugs (and say so); never change rules after the numbers.
7. **Apply the closing rules literally** and write `results.md`: numbers, nulls, costs in R, what closed it or
   what it passed. Never "profitable"; at most "passed these checks, not a proof of edge".
