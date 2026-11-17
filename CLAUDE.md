# Goodbye FuffaGuru — instructions for Claude Code

This project checks, with data, whether what a social-media trading "guru" teaches and shows beats
chance. Your job as the agent: capture, transcribe, extract, verify, preregister, test, report.
Answer the user in their language.

## Python of the project

Use the virtual environment created by `/setup` (`python scripts/bootstrap.py`):
- Windows: `.venv\Scripts\python`
- macOS / Linux: `.venv/bin/python`

Below it is written `PY`. Everything goes through `PY -m fuffaguru <command>` (`--help` lists them).

## The method (details in docs/METHOD.md)

1. Collect public material with the user's own account (`follow`, `history`, `watch`).
2. Transcribe with timestamps and extract frames (done automatically by `history` and the recorder).
3. Extract claims, rules and trades with the templates in `fuffaguru/prompts/` (statuses: taken,
   skipped, drawn, told; notes split into SAID / SEEN / INFERRED).
4. Verify trades on real prices: `PY -m fuffaguru verify trades.csv bars.csv ...`
5. Write the recipe and FREEZE it before any number: `PY -m fuffaguru freeze recipe.json`.
6. Test it: real costs, random direction at the same instants, fake levels, confirmation period,
   related instrument, the recipe without its key filter. Then the Reality Check.

## Rules you must follow

- **Preregistration first.** Recipe, thresholds and closing rules are written and frozen (sha256)
  BEFORE computing any result. After the numbers: no tweaks. A variant is a new recipe, and every
  trial is logged (`fuffaguru.prereg.log_trial`). Apply the closing rules literally.
- **Always run the nulls** (random direction at the same instants, fake levels) and report them,
  whatever they say. Report costs in R. Never call a result "profitable": the best verdict is
  "PASSED THESE CHECKS (NOT A PROOF OF EDGE)".
- **No accusations against people.** Describe rules and trades, never intentions. Words like
  "scammer", "fraud", "liar" are not allowed in any output.
- **Anonymity when sharing.** Anything meant to leave the user's computer (posts, issues, case
  studies) has no names, handles, channel names, exact dates, recognisable quotes or images.
  Inside `data/` the user may keep real names: never copy them into tracked files.
- **Never republish content.** Videos, frames and transcripts of others stay in `data/` (ignored by
  git) and are used only for the user's personal analysis.
- **Respect the platforms.** The user is responsible for the terms of service; do not try to get
  around logins, paywalls, CAPTCHAs or rate limits. If a platform blocks access, stop and tell the user.
- **Secrets.** Never read, print or copy `secrets/`, cookies files, `.env` or tokens. Cookies are read
  only by yt-dlp at run time.
- **After the analysis, clean what is not needed.** When `report.md` and `trades.csv` of a live or
  video folder are written and re-read, run `PY -m fuffaguru clean <folder> --yes` (unless the user
  asked to keep the media). What stays: transcript, trades CSV, report, key-frames image.
- **Ask before changing the system:** installing programs (ffmpeg), `install-autostart`, scheduled
  tasks, Telegram notifications.
- **Do not lose lives:** the watcher must be running when the user follows traders
  (`PY -m fuffaguru status`; start it with `watch --background`).

## Commands (.claude/commands)

| Command | What it does |
|---|---|
| `/setup` | checks Python, ffmpeg, yt-dlp; creates `.venv`; asks which browser holds the user's login |
| `/follow-trader <url or @handle>` | adds the profile, downloads the history, makes sure the live watcher runs |
| `/analyze-live <folder>` | trades taken and skipped with reasons, verified on prices, report, then cleaning |
| `/reverse-engineer <trader>` | rules from transcripts -> recipe -> freeze -> tests against chance |
| `/reality-check <trader>` | the final one-page verdict |
| `/status` | profiles, recordings in progress, last lives, alerts, disk |

Sub-agents (.claude/agents): `trade-extractor` (trades and claims from a session) and `stats-critic`
(looks for reasons why a result is false before anything is concluded).

When the user says "follow these traders": run `/follow-trader` for each, then `/status`.

## Where things are

- Code: `fuffaguru/` (capture/, trades.py, prereg.py, nulltests.py, report.py, recipes.py).
- Captures: `data/<platform>/<handle>/history/<item>/` and `.../live/<YYYYmmdd_HHMMSS>/`.
- Market bars (the user's, never committed): `data/bars/<INSTRUMENT>_M1.csv` with columns
  `time,open,high,low,close` (UTC, bar open time). If missing, ask the user for them.
- Analysis of a trader: `data/<platform>/<handle>/analysis/` (rules.md, recipe.json,
  recipe.frozen.json, trials.jsonl, results, REALITY_CHECK.md).
- Tests: `PY -m pytest`.
