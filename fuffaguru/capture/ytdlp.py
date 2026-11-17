"""Thin wrappers around yt-dlp (https://github.com/yt-dlp/yt-dlp), called as a program.

yt-dlp is the tool that does the real work of reading YouTube, TikTok and
Instagram. We only build its command lines, so they can be printed, tested
and changed easily. Keep yt-dlp up to date (``pip install -U yt-dlp``): the
platforms change often and yt-dlp follows them.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Optional, Sequence


def ytdlp_base() -> list[str]:
    """Prefer the yt-dlp module of this Python, then a yt-dlp program on PATH."""
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        exe = shutil.which("yt-dlp")
        if exe:
            return [exe]
    raise FileNotFoundError("yt-dlp not found: pip install yt-dlp")


def format_selector(max_height: int = 720) -> str:
    """Best video up to ``max_height`` plus audio, else the best single file up to that height."""
    return f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b"


def list_cmd(url: str, cookie_args: Sequence[str] = (), limit: Optional[int] = None,
             base: Optional[list] = None) -> list[str]:
    cmd = list(base or ["yt-dlp"]) + ["--flat-playlist", "--dump-json", "--no-warnings", *cookie_args]
    if limit:
        cmd += ["--playlist-end", str(int(limit))]
    return cmd + [url]


def download_cmd(url: str, out_template: str, archive: str, cookie_args: Sequence[str] = (),
                 max_height: int = 720, date_after: Optional[str] = None, base: Optional[list] = None) -> list[str]:
    cmd = list(base or ["yt-dlp"]) + [
        "--no-playlist", "-f", format_selector(max_height), "--merge-output-format", "mp4",
        "--write-info-json", "--no-write-comments", "--download-archive", archive,
        "--no-warnings", "-o", out_template, *cookie_args,
    ]
    if date_after:
        cmd += ["--dateafter", date_after]
    return cmd + [url]


def probe_live_cmd(url: str, cookie_args: Sequence[str] = (), base: Optional[list] = None) -> list[str]:
    """yt-dlp -J on a live page: tells if it is live and lists the stream formats."""
    return list(base or ["yt-dlp"]) + ["-J", "--no-warnings", "--no-playlist", *cookie_args, url]


def live_from_start_cmd(url: str, out_template: str, cookie_args: Sequence[str] = (), max_height: int = 720,
                        base: Optional[list] = None) -> list[str]:
    """YouTube: record the whole live from its beginning (one file, no pieces)."""
    return list(base or ["yt-dlp"]) + [
        "--live-from-start", "--wait-for-video", "30", "-f", format_selector(max_height),
        "--no-warnings", "-o", out_template, *cookie_args, url,
    ]


def run_json(cmd: Sequence[str], timeout: float = 120.0) -> Optional[dict]:
    """Run a yt-dlp command that prints one JSON document; None on failure."""
    proc = subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def run_json_lines(cmd: Sequence[str], timeout: float = 600.0) -> list[dict]:
    proc = subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    items = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return items


def pick_live_stream(info: dict, max_height: int = 720) -> Optional[str]:
    """From a yt-dlp JSON of a live: the URL of the best format with video *and* audio."""
    formats = info.get("formats") or []
    muxed = [f for f in formats
             if f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none") and f.get("url")]
    if not muxed:
        return info.get("url") if info.get("vcodec") not in (None, "none") else None
    under = [f for f in muxed if (f.get("height") or 0) <= max_height] or muxed
    best = max(under, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0))
    return best["url"]


def is_live_info(info: Optional[dict]) -> bool:
    return bool(info) and (info.get("live_status") == "is_live" or info.get("is_live") is True)
