"""Profiles to follow: parse a URL or a handle, store the list in ``data/profiles.json``."""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

PLATFORMS = ("youtube", "tiktok", "instagram")
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class Profile:
    platform: str
    handle: str               # without '@'; for YouTube it can also be a channel id 'UC...'
    added_utc: str = ""
    note: str = ""

    @property
    def key(self) -> str:
        return f"{self.platform}:{self.handle}"

    @property
    def slug(self) -> str:
        return _SAFE.sub("_", self.handle)

    def folder(self, data_dir: Path) -> Path:
        return Path(data_dir) / self.platform / self.slug

    # -------------------------------------------------------------- URLs
    @property
    def page_url(self) -> str:
        if self.platform == "tiktok":
            return f"https://www.tiktok.com/@{self.handle}"
        if self.platform == "instagram":
            return f"https://www.instagram.com/{self.handle}/"
        if self.handle.startswith("UC") and len(self.handle) == 24:
            return f"https://www.youtube.com/channel/{self.handle}"
        return f"https://www.youtube.com/@{self.handle}"

    @property
    def live_url(self) -> str:
        if self.platform == "tiktok":
            return f"https://www.tiktok.com/@{self.handle}/live"
        if self.platform == "instagram":
            return f"https://www.instagram.com/{self.handle}/live/"
        return self.page_url + "/live"

    def history_urls(self) -> list[str]:
        """Listing pages for the public history (videos, shorts, reels, past lives)."""
        if self.platform == "youtube":
            return [self.page_url + tab for tab in ("/videos", "/shorts", "/streams")]
        if self.platform == "instagram":
            return [self.page_url + "reels/", self.page_url]
        return [self.page_url]


def parse_profile(text: str, platform: Optional[str] = None) -> Profile:
    """Accept a profile URL or a handle ('@name' needs ``platform``)."""
    text = text.strip()
    if "://" in text or text.startswith(("www.", "youtube.", "tiktok.", "instagram.")):
        url = text if "://" in text else "https://" + text
        u = urlparse(url)
        host = (u.hostname or "").lower()
        parts = [p for p in u.path.split("/") if p]
        if "tiktok.com" in host:
            handle = next((p[1:] for p in parts if p.startswith("@")), None)
            if not handle:
                raise ValueError(f"no @handle in TikTok URL: {text}")
            return Profile("tiktok", handle)
        if "instagram.com" in host:
            if not parts:
                raise ValueError(f"no account name in Instagram URL: {text}")
            return Profile("instagram", parts[0])
        if "youtube.com" in host or "youtu.be" in host:
            if parts and parts[0].startswith("@"):
                return Profile("youtube", parts[0][1:])
            if len(parts) >= 2 and parts[0] in ("channel", "c", "user"):
                return Profile("youtube", parts[1])
            raise ValueError(f"use the channel URL (youtube.com/@name or /channel/ID): {text}")
        raise ValueError(f"unsupported site: {host}")
    if not platform:
        raise ValueError("a bare handle needs --platform youtube|tiktok|instagram")
    platform = platform.lower()
    if platform not in PLATFORMS:
        raise ValueError(f"platform must be one of {PLATFORMS}")
    return Profile(platform, text.lstrip("@"))


class ProfileStore:
    """The list of followed profiles (a small JSON file in the data folder)."""

    def __init__(self, data_dir):
        self.path = Path(data_dir) / "profiles.json"

    def all(self) -> list[Profile]:
        if not self.path.exists():
            return []
        return [Profile(**p) for p in json.loads(self.path.read_text(encoding="utf-8"))]

    def _save(self, profiles: list[Profile]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(p) for p in profiles], indent=2) + "\n", encoding="utf-8")

    def add(self, profile: Profile) -> Profile:
        profiles = self.all()
        for p in profiles:
            if p.key == profile.key:
                return p
        if not profile.added_utc:
            profile.added_utc = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        profiles.append(profile)
        self._save(profiles)
        return profile

    def remove(self, key: str) -> bool:
        profiles = self.all()
        keep = [p for p in profiles if p.key != key]
        self._save(keep)
        return len(keep) != len(profiles)

    def get(self, key: str) -> Optional[Profile]:
        return next((p for p in self.all() if p.key == key), None)
