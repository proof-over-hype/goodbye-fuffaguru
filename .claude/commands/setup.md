---
description: Check Python, ffmpeg and yt-dlp, create the virtual environment, choose the browser for cookies
---

Set up the project for the user.

1. Check `python --version` (3.9 or newer is needed) and whether `ffmpeg` and `ffprobe` are on PATH.
2. Ask the user which browser they are logged in with on YouTube / TikTok / Instagram
   (firefox, chrome, edge, brave, chromium, opera, vivaldi, safari), or whether they prefer to export
   a `cookies.txt` into `secrets/`. Explain that cookies are never copied into the repository, and
   that on Windows recent Chrome/Edge block cookie reading while open (Firefox or cookies.txt work).
3. Run `python scripts/bootstrap.py --browser <choice>` (use `file` for cookies.txt). It creates
   `.venv`, installs the project with its extras and writes `config/settings.json`.
4. If ffmpeg is missing, give the install command for the user's system
   (Windows: `winget install Gyan.FFmpeg`; macOS: `brew install ffmpeg`; Linux: `sudo apt install ffmpeg`)
   and ask before running anything that installs software.
5. Run the tests: `PY -m pytest` (PY = `.venv\Scripts\python` on Windows, `.venv/bin/python` elsewhere).
6. Tell the user what is ready and suggest `/follow-trader <url>`. Ask whether they want the watcher
   to restart by itself after a reboot (`PY -m fuffaguru install-autostart`); install it only on a yes.
