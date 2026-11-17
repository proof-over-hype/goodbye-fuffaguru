"""Guided setup: check the tools, choose where your cookies come from, create the folders."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from typing import Callable, Optional

from .settings import Settings

BROWSERS = ("firefox", "chrome", "edge", "brave", "chromium", "opera", "vivaldi", "safari")


def check_tools() -> list[tuple[str, bool, str]]:
    """(name, ok, hint) for each tool the project uses."""
    def has_module(name: str) -> bool:
        return importlib.util.find_spec(name) is not None

    return [
        ("Python >= 3.9", sys.version_info >= (3, 9), f"you have {sys.version.split()[0]}"),
        ("ffmpeg", shutil.which("ffmpeg") is not None, "https://ffmpeg.org/download.html (or winget/brew/apt install ffmpeg)"),
        ("ffprobe", shutil.which("ffprobe") is not None, "comes with ffmpeg"),
        ("yt-dlp", has_module("yt_dlp") or shutil.which("yt-dlp") is not None, "pip install -U yt-dlp"),
        ("faster-whisper", has_module("faster_whisper"), "pip install faster-whisper (transcription)"),
        ("numpy + pandas", has_module("numpy") and has_module("pandas"), "pip install -e ."),
        ("Pillow (key frames image)", has_module("PIL"), "pip install pillow (optional)"),
    ]


def run_setup(settings: Settings, browser: Optional[str] = None, ask: Callable[[str], str] = input,
              interactive: bool = True, out: Callable[[str], None] = print) -> Settings:
    out("Goodbye FuffaGuru - setup\n")
    for name, ok, hint in check_tools():
        out(f"  [{'ok' if ok else 'MISSING'}] {name}" + ("" if ok else f"  -> {hint}"))
    out("")
    out("Your account, your cookies: the tools read pages as YOU, with the session of your browser.")
    out("Nothing secret is saved in the project. On Windows, recent Chrome/Edge block cookie reading:")
    out("Firefox works, or export a cookies.txt into the 'secrets' folder (ignored by git).\n")
    choice = browser
    if choice is None and interactive:
        choice = ask(f"Browser to read cookies from ({', '.join(BROWSERS)}), 'file' for secrets/cookies.txt, "
                     "or empty for none: ").strip().lower()
    if choice:
        if choice == "file":
            settings.values["cookies"]["browser"] = None
            out(f"  cookies from {settings['cookies']['file']} (export it yourself; never commit it)")
        elif choice in BROWSERS:
            settings.values["cookies"]["browser"] = choice
            out(f"  cookies from the {choice} browser")
        else:
            out(f"  unknown browser '{choice}': cookies not configured")
    for folder in (settings.data_dir, settings.root / "secrets", settings.root / "config"):
        folder.mkdir(parents=True, exist_ok=True)
    path = settings.save()
    out(f"\nSettings saved in {path.relative_to(settings.root)}. Data will go to "
        f"{settings.data_dir.relative_to(settings.root) if settings.data_dir.is_relative_to(settings.root) else settings.data_dir}.")
    out("Next: 'follow <url or @handle> --platform tiktok', then 'watch' (or 'install-autostart').")
    return settings
