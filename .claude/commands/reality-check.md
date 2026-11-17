---
description: Write the final Reality Check of a trader - claims vs data, verified trades, recipe tests, red flags, verdict
argument-hint: <profile key or handle>
---

Write the Reality Check for: $ARGUMENTS

PY = `.venv\Scripts\python` on Windows, `.venv/bin/python` elsewhere.

1. Gather: every `live/*/trades.csv` and `report.md`, `analysis/rules.md`, `analysis/results.md`,
   `analysis/trials.jsonl`, the claims recorded in `claims.md` files.
2. Merge the trades of all analysed sessions into `analysis/all_trades.csv` and run
   `PY -m fuffaguru verify analysis/all_trades.csv <bars> --cost <c> --trials <number of lines in trials.jsonl>
   --claimed-win-rate <claimed, 0-1> --claimed-basis <trades|days|unknown> --report analysis/verified_report.md`.
3. Go through `docs/RED_FLAGS.md` and mark which flags are observed, each with the evidence (file and timestamp).
4. Write `analysis/REALITY_CHECK.md`, one page:
   - verdict: INCONCLUSIVE / NO EVIDENCE OF EDGE / PASSED THESE CHECKS (NOT A PROOF OF EDGE);
   - claimed vs measured (win rate per trade and per day, frequency, returns);
   - verified live trades (taken only) and what happened to skipped ones;
   - the preregistered recipe: fingerprint, closing rules, results and nulls;
   - red flags observed; what is missing to say more (e.g. more lives, bars, a third-party track record);
   - the caveats: not financial advice; rules and trades, not people.
5. Give the user the verdict in a few lines. If they want to share it, produce an anonymous version
   (no names, handles, channels, exact dates, quotes or images) and remind them not to republish content.
