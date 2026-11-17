"""Use the user's own logged-in session, without storing any secret in the repository.

Two ways, chosen in the settings:

* ``browser``: yt-dlp reads the cookies of the browser where *you* are logged
  in (``--cookies-from-browser``). Nothing is copied into the project.
  Note: on Windows, recent Chrome and Edge versions block this while the
  browser is open; Firefox works, or use a cookies.txt file.
* ``file``: a cookies.txt (Netscape format) that you export yourself, e.g.
  with a browser extension, into ``secrets/`` (ignored by git).

Cookies are personal: never commit them, never share them, never paste them
into an issue or a chat.
"""

from __future__ import annotations

import http.cookiejar
import urllib.request
from pathlib import Path
from typing import Optional

from .settings import Settings

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def ytdlp_cookie_args(settings: Settings) -> list[str]:
    c = settings["cookies"]
    if c.get("browser"):
        spec = c["browser"] + (f":{c['browser_profile']}" if c.get("browser_profile") else "")
        return ["--cookies-from-browser", spec]
    if c.get("file"):
        path = settings.resolve(c["file"])
        if path.exists():
            return ["--cookies", str(path)]
    return []


def load_cookiejar(settings: Settings) -> Optional[http.cookiejar.CookieJar]:
    """A cookie jar for direct page reads (live detection). None if no cookies are configured."""
    c = settings["cookies"]
    if c.get("browser"):
        try:
            from yt_dlp.cookies import extract_cookies_from_browser
        except ImportError as exc:
            raise ImportError("reading browser cookies needs yt-dlp: pip install yt-dlp") from exc
        return extract_cookies_from_browser(c["browser"], c.get("browser_profile"))
    if c.get("file"):
        path = settings.resolve(c["file"])
        if path.exists():
            jar = http.cookiejar.MozillaCookieJar(str(path))
            jar.load(ignore_discard=True, ignore_expires=True)
            return jar
    return None


def fetch_text(url: str, jar=None, headers: Optional[dict] = None, timeout: float = 20.0) -> str:
    """GET a page with the user's cookies and a normal browser user agent."""
    handlers = [urllib.request.HTTPCookieProcessor(jar)] if jar is not None else []
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8",
                                               **(headers or {})})
    with opener.open(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")
