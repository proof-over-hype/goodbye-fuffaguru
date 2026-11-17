"""Is the profile live right now, and where is the stream?

Each detector returns a ``LiveStatus``:

* ``live=False``: not live (or the page could not be read);
* ``live=True`` with ``stream_url``: live, and a stream to record was found;
* ``live=True`` without ``stream_url``: the page says live but no usable
  stream was found. The recorder retries and, after a few checks, alerts the
  user instead of staying silent (this is how a whole live can be lost).

TikTok, what we learned the hard way:

* yt-dlp sometimes answers "not live" while the profile is live, so we read
  the ``/@name/live`` page ourselves, with the user's cookies;
* the bare ``pull-*.flv`` address answers 403: only the *signed* one, with
  its query string, works. In the page it is escaped (``\\u0026`` for ``&``);
* the host changes (``pull-flv-...``, ``pull-f5-...``) and so does the path
  (``/game/``, ``/stage/``...): accept any ``pull-*`` host except
  ``pull-hls``, and any folder;
* drop the ``only_audio`` variants;
* check with ffprobe that the stream has both video and audio.

Instagram live is EXPERIMENTAL and untested against a real live: the private
web API changes often. See docs/CAPTURE.md.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlparse

from . import ytdlp
from .cookies import fetch_text, load_cookiejar, ytdlp_cookie_args
from .profiles import Profile
from .settings import Settings


@dataclass
class LiveStatus:
    live: bool
    stream_url: Optional[str] = None
    reason: str = ""


# ------------------------------------------------------------------ helpers

_ESCAPES = [
    (re.compile(r"\\+u0026", re.I), "&"),
    (re.compile(r"\\+u002f", re.I), "/"),
    (re.compile(r"\\+u003d", re.I), "="),
    (re.compile(r"\\+/"), "/"),
]


def unescape_url(raw: str) -> str:
    """Undo JSON/HTML escaping of a URL found inside a page (any depth of backslashes)."""
    url = raw
    for pattern, repl in _ESCAPES:
        url = pattern.sub(repl, url)
    return url.replace("&amp;", "&").replace("\\", "").strip()


_TIKTOK_PULL = re.compile(r"https?:(?:\\*/){2}pull-[^\s\"'<>]+", re.I)
_QUALITY = [("_or4", 0), ("origin", 0), ("_uhd", 1), ("_hd", 2), ("_sd", 3), ("_ld", 4)]


def tiktok_quality_rank(url: str) -> int:
    low = url.lower()
    path = urlparse(low).path
    for key, rank in _QUALITY:
        if key in path:
            return rank
    return 5


def extract_tiktok_stream_urls(text: str) -> list[str]:
    """All usable signed FLV addresses in a TikTok page or API answer, best first."""
    found, seen = [], set()
    for raw in _TIKTOK_PULL.findall(text):
        url = unescape_url(raw)
        p = urlparse(url)
        host = (p.hostname or "").lower()
        if not host.startswith("pull-") or host.startswith("pull-hls"):
            continue
        if not p.path.lower().endswith(".flv") or not p.query:
            continue  # unsigned address: 403
        if "only_audio" in url.lower():
            continue
        if url not in seen:
            seen.add(url)
            found.append(url)
    return sorted(found, key=tiktok_quality_rank)


_LIVE_MARKERS = [
    re.compile(r'"isLive"\s*:\s*true', re.I),
    re.compile(r'"liveRoom"\s*:\s*\{[^{}]{0,400}?"status"\s*:\s*2\b', re.S),
    re.compile(r'"LiveRoom"[^{}]{0,50}\{[^{}]{0,400}?"status"\s*:\s*2\b', re.S),
]
_ROOM_ID = re.compile(r'"roomId"\s*:\s*"(\d{6,})"')


def tiktok_page_says_live(text: str) -> bool:
    return any(p.search(text) for p in _LIVE_MARKERS)


def tiktok_room_id(text: str) -> Optional[str]:
    m = _ROOM_ID.search(text)
    return m.group(1) if m else None


def find_urls_with_extension(text: str, ext: str) -> list[str]:
    """Generic: escaped or plain https URLs whose path ends with ``ext`` (e.g. '.mpd')."""
    out = []
    for raw in re.findall(r"https?:(?:\\*/){2}[^\s\"'<>]+", text):
        url = unescape_url(raw)
        if urlparse(url).path.lower().endswith(ext) and url not in out:
            out.append(url)
    return out


# ------------------------------------------------------------------- ffprobe


def ffprobe_cmd(url: str, ffprobe: str = "ffprobe", timeout_s: int = 15) -> list[str]:
    return [ffprobe, "-v", "error", "-rw_timeout", str(timeout_s * 1_000_000), "-show_entries",
            "stream=codec_type", "-of", "json", url]


def parse_ffprobe_streams(output: str) -> set[str]:
    try:
        data = json.loads(output or "{}")
    except json.JSONDecodeError:
        return set()
    return {s.get("codec_type") for s in data.get("streams", []) if s.get("codec_type")}


def has_video_and_audio(url: str, runner: Callable = subprocess.run) -> bool:
    """True if ffprobe sees both a video and an audio stream at ``url``."""
    exe = shutil.which("ffprobe") or "ffprobe"
    try:
        proc = runner(ffprobe_cmd(url, exe), capture_output=True, text=True, timeout=40)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return {"video", "audio"} <= parse_ffprobe_streams(proc.stdout)


# ----------------------------------------------------------------- detectors


class Detector:
    """Base class: ``check(profile) -> LiveStatus``."""

    def __init__(self, settings: Settings, fetch: Callable = fetch_text, run_json: Callable = ytdlp.run_json):
        self.settings = settings
        self._fetch = fetch
        self._run_json = run_json
        self._jar = None
        self._jar_loaded = False

    def jar(self):
        if not self._jar_loaded:
            self._jar = load_cookiejar(self.settings)
            self._jar_loaded = True
        return self._jar

    def fetch(self, url: str, headers: Optional[dict] = None) -> str:
        return self._fetch(url, self.jar(), headers)

    def ytdlp_info(self, url: str) -> Optional[dict]:
        try:
            base = ytdlp.ytdlp_base()
        except FileNotFoundError:
            return None
        return self._run_json(ytdlp.probe_live_cmd(url, ytdlp_cookie_args(self.settings), base=base))

    def check(self, profile: Profile) -> LiveStatus:  # pragma: no cover - interface
        raise NotImplementedError


class TikTokDetector(Detector):
    WEBCAST = "https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={room}"

    def check(self, profile: Profile) -> LiveStatus:
        try:
            page = self.fetch(profile.live_url, {"Referer": "https://www.tiktok.com/"})
        except Exception as exc:  # network errors, 4xx/5xx
            return LiveStatus(False, None, f"page not readable: {exc}")
        urls = extract_tiktok_stream_urls(page)
        says_live = tiktok_page_says_live(page)
        room = tiktok_room_id(page)
        if not urls and room and says_live:
            # Same signed addresses from the room information used by many open-source recorders.
            try:
                api = self.fetch(self.WEBCAST.format(room=room), {"Referer": "https://www.tiktok.com/"})
                urls = extract_tiktok_stream_urls(api)
            except Exception:
                pass
        if not urls and says_live:
            info = self.ytdlp_info(profile.live_url)
            if ytdlp.is_live_info(info):
                url = ytdlp.pick_live_stream(info, self.settings["download"]["max_height"])
                if url:
                    urls = [url]
        if urls:
            return LiveStatus(True, urls[0], "signed stream found")
        if says_live:
            return LiveStatus(True, None, "page says live, no usable stream address")
        return LiveStatus(False, None, "not live")


class YouTubeDetector(Detector):
    def check(self, profile: Profile) -> LiveStatus:
        info = self.ytdlp_info(profile.live_url)
        if not ytdlp.is_live_info(info):
            return LiveStatus(False, None, "not live")
        url = ytdlp.pick_live_stream(info, self.settings["download"]["max_height"])
        if url:
            return LiveStatus(True, url, "live manifest found")
        return LiveStatus(True, None, "live, but no format with video and audio")


class InstagramDetector(Detector):
    """EXPERIMENTAL. 1) yt-dlp on the live page; 2) the DASH manifest (.mpd) from the
    web API, read with the user's logged-in cookies. Untested against a real live."""

    APP_ID = {"X-IG-App-ID": "936619743392459", "Referer": "https://www.instagram.com/"}
    PROFILE_API = "https://www.instagram.com/api/v1/users/web_profile_info/?username={user}"
    LIVE_API = "https://www.instagram.com/api/v1/live/web_info/?target_user_id={uid}"

    def check(self, profile: Profile) -> LiveStatus:
        info = self.ytdlp_info(profile.live_url)
        if ytdlp.is_live_info(info):
            url = ytdlp.pick_live_stream(info, self.settings["download"]["max_height"])
            return LiveStatus(True, url, "yt-dlp" if url else "live, no stream from yt-dlp")
        try:
            prof = json.loads(self.fetch(self.PROFILE_API.format(user=profile.handle), self.APP_ID))
            uid = prof["data"]["user"]["id"]
            live_text = self.fetch(self.LIVE_API.format(uid=uid), self.APP_ID)
        except Exception as exc:
            return LiveStatus(False, None, f"instagram api not readable: {exc}")
        mpds = find_urls_with_extension(live_text, ".mpd")
        if mpds:
            return LiveStatus(True, mpds[0], "dash manifest found (experimental)")
        if re.search(r'"broadcast_status"\s*:\s*"active"', live_text):
            return LiveStatus(True, None, "broadcast active, no manifest found (experimental)")
        return LiveStatus(False, None, "not live")


def detector_for(profile: Profile, settings: Settings) -> Detector:
    return {"tiktok": TikTokDetector, "youtube": YouTubeDetector, "instagram": InstagramDetector}[profile.platform](settings)
