"""Download the public history of a profile (videos, shorts, reels, clips, past lives).

Steps for each item: list -> download at 720p at most (with its info JSON) ->
transcript + frames -> delete the video (default policy). Items already done
are skipped, so the command can be run again to fetch only what is new.

Limits, honestly:
* YouTube: channel tabs /videos, /shorts and /streams work well with yt-dlp;
* TikTok: the profile listing often needs your logged-in cookies, and can
  still fail when TikTok changes its pages; update yt-dlp first;
* Instagram: yt-dlp's profile listing has been unreliable for years. If it
  fails, put the post/reel URLs in a text file and use ``--urls FILE``.
"""

from __future__ import annotations

import copy
import json
import logging
import subprocess
from pathlib import Path
from typing import Callable, Optional

from . import ytdlp
from .cookies import ytdlp_cookie_args
from .notify import Notifier
from .process import MediaProcessor
from .profiles import Profile
from .retention import MEDIA_EXT, disk_ok
from .settings import Settings

log = logging.getLogger("goodbye_fuffaguru")


def _item_url(entry: dict, profile: Profile) -> Optional[str]:
    url = entry.get("webpage_url") or entry.get("url")
    if url and url.startswith("http"):
        return url
    if profile.platform == "youtube" and entry.get("id"):
        return f"https://www.youtube.com/watch?v={entry['id']}"
    return None


def list_items(profile: Profile, settings: Settings, limit: Optional[int] = None,
               run_lines: Callable = ytdlp.run_json_lines) -> list[dict]:
    base = ytdlp.ytdlp_base()
    items, seen = [], set()
    for url in profile.history_urls():
        for e in run_lines(ytdlp.list_cmd(url, ytdlp_cookie_args(settings), limit, base=base)):
            u = _item_url(e, profile)
            key = e.get("id") or u
            if u and key not in seen:
                seen.add(key)
                items.append({"id": str(e.get("id") or abs(hash(u))), "url": u, "title": e.get("title", ""),
                              "duration": e.get("duration"), "upload_date": e.get("upload_date")})
    return items


def download_history(profile: Profile, settings: Settings, *, limit: Optional[int] = None,
                     date_after: Optional[str] = None, keep_media: bool = False, urls: Optional[list] = None,
                     run: Callable = subprocess.run, run_lines: Callable = ytdlp.run_json_lines,
                     processor: Optional[MediaProcessor] = None, notifier: Optional[Notifier] = None) -> dict:
    notifier = notifier or Notifier(settings)
    if keep_media:
        settings = copy.copy(settings)
        settings.values = copy.deepcopy(settings.values)
        settings.values["retention"]["delete_media_after_transcription"] = False
    folder = profile.folder(settings.data_dir) / "history"
    folder.mkdir(parents=True, exist_ok=True)
    limit = limit or int(settings["download"]["default_limit"])
    if urls:
        items = [{"id": f"url{i:04d}", "url": u, "title": ""} for i, u in enumerate(urls, 1)]
    else:
        items = list_items(profile, settings, limit, run_lines=run_lines)
    with (folder / "items.jsonl").open("a", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    processor = processor or MediaProcessor(settings)
    base = ytdlp.ytdlp_base()
    done = skipped = failed = 0
    for it in items[:limit]:
        out = folder / it["id"]
        if (out / "transcript" / "video.md").exists():
            skipped += 1
            continue
        if not disk_ok(settings, notifier):
            log.warning("stopping downloads: low disk space")
            break
        cmd = ytdlp.download_cmd(it["url"], str(out / "video.%(ext)s"), str(folder / "archive.txt"),
                                 ytdlp_cookie_args(settings), settings["download"]["max_height"], date_after, base=base)
        run(cmd, capture_output=True, text=True)
        media = [p for p in out.glob("video.*") if p.suffix.lower() in MEDIA_EXT and p.suffix != ".part"]
        if not media:
            failed += 1
            log.warning("no media downloaded for %s", it["url"])
            continue
        try:
            processor.process(media[0], out, name="video")
            done += 1
        except ImportError as exc:
            log.warning("transcription unavailable (%s): videos are kept", exc)
            done += 1
        except Exception as exc:
            failed += 1
            log.warning("processing failed for %s: %s", it["url"], exc)
    return {"listed": len(items), "processed": done, "skipped": skipped, "failed": failed, "folder": str(folder)}
