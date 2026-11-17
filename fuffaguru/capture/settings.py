"""Settings of the capture tools, stored in ``config/settings.json`` (ignored by git).

Every path is relative to the *root* folder (the repository folder by
default). Nothing secret is ever written here: cookies stay in the user's
browser, or in a cookies.txt file inside ``secrets/`` (also ignored by git).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Optional

DEFAULTS: dict = {
    "data_dir": "data",
    "cookies": {
        # One of: chrome, firefox, edge, brave, chromium, opera, vivaldi, safari, or null.
        "browser": None,
        "browser_profile": None,
        # Alternative to the browser: a cookies.txt (Netscape format) exported by the user.
        "file": "secrets/cookies.txt",
    },
    "watch": {
        "interval_seconds": 60,          # how often each profile is checked for a live
        "segment_seconds": 180,          # length of each recorded piece
        "end_checks": 3,                 # consecutive "not live" checks before closing a session
        "end_check_interval_seconds": 60,
        "retry_seconds": 20,             # wait when the page says live but no stream is found
        "stream_missing_alert_after": 3, # alert after this many "live but no stream" checks
        "stale_lock_seconds": 600,
        "youtube_live_from_start": False,
    },
    "download": {"max_height": 720, "default_limit": 50},
    "transcription": {"model": "small", "language": None, "device": "auto", "compute_type": "default"},
    "frames": {"every_seconds": 2, "sheet_every_seconds": 10, "sheet_cols": 4, "sheet_rows": 4},
    "retention": {
        "delete_media_after_transcription": True,  # video, audio and live pieces go once transcribed
        "delete_frames_after_analysis": True,      # frames and contact sheets go once the analysis is written
        "key_frames": 6,                           # frames kept in one image after cleaning (4-6)
        "min_free_gb": 20,                         # no recording or download below this free space
    },
    "notify": {
        "desktop": True,
        "telegram": False,
        # Names of the environment variables holding your bot token and chat id (never the values).
        "telegram_token_env": "GFG_TELEGRAM_TOKEN",
        "telegram_chat_env": "GFG_TELEGRAM_CHAT_ID",
    },
}


def _merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class Settings:
    """Settings plus the root folder they refer to."""

    def __init__(self, root=None, values: Optional[dict] = None):
        self.root = Path(root or Path.cwd()).resolve()
        self.values = _merge(DEFAULTS, values or {})

    # ------------------------------------------------------------------ files
    @property
    def path(self) -> Path:
        return self.root / "config" / "settings.json"

    @classmethod
    def load(cls, root=None) -> "Settings":
        s = cls(root)
        if s.path.exists():
            s.values = _merge(DEFAULTS, json.loads(s.path.read_text(encoding="utf-8")))
        return s

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.values, indent=2) + "\n", encoding="utf-8")
        return self.path

    # ---------------------------------------------------------------- helpers
    def __getitem__(self, key):
        return self.values[key]

    @property
    def data_dir(self) -> Path:
        p = Path(self.values["data_dir"])
        return p if p.is_absolute() else self.root / p

    @property
    def logs_dir(self) -> Path:
        d = self.data_dir / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def resolve(self, relative) -> Path:
        p = Path(relative)
        return p if p.is_absolute() else self.root / p
