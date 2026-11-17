---
description: Analyse one recorded live (or video) folder - trades taken and skipped with reasons, verified on prices, then clean up
argument-hint: <session folder, e.g. data/tiktok/name/live/20250106_150000>
---

Analyse the folder: $ARGUMENTS

PY = `.venv\Scripts\python` on Windows, `.venv/bin/python` elsewhere.

1. **Read** `session.json`, `events.log` (gaps, ffmpeg restarts, alerts) and `transcript.md`. If the session
   is still `recording`, stop and tell the user.
2. **Look at the charts**: open the contact sheets in `sheets/` and, around the minutes where trades are
   discussed, the frames in `frames/` (one every 2 s). Read instrument, timeframe, price axis, position boxes,
   order panels, P/L. Note the chart's time zone.
3. **Extract the trades** with the `trade-extractor` sub-agent (or the template
   `fuffaguru/prompts/extract_trades.md`). Write `trades.csv` in the folder, schema of
   `examples/trades_template.csv`: every trade TAKEN, SKIPPED (with the reason in notes), DRAWN or TOLD.
   Also write the claims and contradictions in `claims.md`.
4. **Verify on prices**: find the user's bars in `data/bars/<INSTRUMENT>_M1.csv`. If missing, ask for them
   and skip this step. Run
   `PY -m fuffaguru verify <folder>/trades.csv <bars> --cost <round trip> --out <folder>/verified.csv --report <folder>/verify_report.md`.
   Check first that a candle shown on screen matches the bars (time zone, instrument, futures vs CFD offset).
5. **Write `report.md`** (short, factual, no judgement of the person): what happened in the live; trades taken
   and skipped with reasons; how each ended on real prices, including "right direction, wrong stop"; claims vs
   observation; which lessons of `docs/LESSONS.md` (A1-A9) apply. Write `key_frames.txt` with 4-6 frame paths
   (relative to the folder) that show the key moments.
6. **Re-read** `report.md` and `trades.csv` to make sure they are complete and readable.
7. **Clean** (project rule: after the analysis, delete what is not needed):
   `PY -m fuffaguru clean <folder> --yes` - unless the user asked to keep the media (`--keep-media`).
   It keeps transcript, trades CSV, report and a key-frames image, and logs every deletion.
8. Tell the user the outcome in a few lines and the space freed.
