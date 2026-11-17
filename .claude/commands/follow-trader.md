---
description: Follow a trader - add the profile, download the public history, make sure the live watcher runs
argument-hint: <profile URL, or @handle plus platform>
---

Follow the trader given in: $ARGUMENTS

PY = `.venv\Scripts\python` on Windows, `.venv/bin/python` elsewhere. If `.venv` is missing, run `/setup` first.

1. Add the profile: `PY -m fuffaguru follow <url>` (a bare `@handle` needs `--platform youtube|tiktok|instagram`;
   ask the user if unclear). Note the profile key it prints (e.g. `tiktok:name`).
2. Download the public history: `PY -m fuffaguru history <key> --limit 30` (ask the user if they want more).
   It downloads at 720p at most, transcribes, extracts frames and deletes the videos.
   - Instagram profile listings often fail: if so, ask the user for a list of post/reel URLs and use `--urls FILE`.
   - If yt-dlp fails for login reasons, tell the user to check they are logged in in the browser chosen in setup
     and to update yt-dlp (`PY -m pip install -U yt-dlp`). Never try to bypass a login or a CAPTCHA.
3. Make sure lives are not lost: `PY -m fuffaguru status`. If the watcher's last round is missing or old,
   start it with `PY -m fuffaguru watch --background`. Suggest `install-autostart` (only with the user's yes).
4. One quick check of the live page: `PY -m fuffaguru check-live <key>` and report the answer.
5. Summarise for the user: profile key, items downloaded and transcribed, watcher state, disk space.

Rules: the user's own account and cookies only; personal analysis only; nothing captured is ever republished
or copied into tracked files.
