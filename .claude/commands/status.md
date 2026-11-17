---
description: Show followed profiles, recordings in progress, last lives, alerts, errors and disk space
---

PY = `.venv\Scripts\python` on Windows, `.venv/bin/python` elsewhere.

1. Run `PY -m fuffaguru status`.
2. Summarise for the user in a few lines: which profiles are followed, which are recording now, the last lives
   (ended, transcribed, analysed or not), alerts and errors, free disk space.
3. If the watcher's last round is missing or older than 5 minutes, say that lives may be lost and offer to start it
   (`PY -m fuffaguru watch --background`).
4. If there are ended lives not yet analysed, offer `/analyze-live <folder>`. If disk space is low, offer `clean`
   on analysed folders.
