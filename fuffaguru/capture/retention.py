"""What to keep, what to delete, and when: save disk without losing evidence.

Default policy (configurable in ``config/settings.json`` -> ``retention``):

1. once a video, an audio file or a live piece is transcribed and its frames
   are extracted, the media file is deleted;
2. once the analysis of a live or a video is written, the frames and contact
   sheets are deleted, after saving 4-6 key frames in one image;
3. what stays: the transcript, the trades CSV, the report and the key-frames
   image.

Safety: step 2 runs only if ``report.md`` and ``trades.csv`` exist and can be
read back. If either is missing, nothing is deleted. Every deletion is
written to ``data/logs/deletions.jsonl``.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .settings import Settings

MEDIA_EXT = {".mp4", ".mkv", ".webm", ".flv", ".ts", ".m4a", ".mp3", ".wav", ".opus", ".aac", ".mov", ".part"}
REPORT_NAME = "report.md"
TRADES_NAME = "trades.csv"
KEY_FRAMES_NAME = "key_frames.jpg"
KEY_FRAMES_LIST = "key_frames.txt"
FRAME_DIRS = ("frames", "sheets")


# ------------------------------------------------------------------ disk space


def free_gb(path) -> float:
    path = Path(path)
    while not path.exists() and path != path.parent:
        path = path.parent
    return shutil.disk_usage(path).free / 1024 ** 3


def disk_ok(settings: Settings, notifier=None, free: Callable = free_gb) -> bool:
    """False (and an alert) when free space is below ``retention.min_free_gb``."""
    minimum = float(settings["retention"]["min_free_gb"])
    have = free(settings.data_dir)
    if have < minimum:
        if notifier:
            notifier.alert("Low disk space", f"{have:.1f} GB free, minimum {minimum:g} GB: recording and "
                           "downloading are stopped. Run 'clean' or free some space.")
        return False
    return True


# ---------------------------------------------------------------------- logging


def log_deletion(settings: Settings, path: Path, size: int, reason: str) -> None:
    line = {"time": _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "path": str(Path(path).relative_to(settings.root)) if str(path).startswith(str(settings.root)) else str(path),
            "bytes": size, "reason": reason}
    with (settings.logs_dir / "deletions.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line) + "\n")


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def delete_path(settings: Settings, path: Path, reason: str) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    size = _size(path)
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    log_deletion(settings, path, size, reason)
    return size


# --------------------------------------------------------- media after transcript


def transcript_readable(path: Path) -> bool:
    try:
        return Path(path).exists() and len(Path(path).read_text(encoding="utf-8").strip()) > 0
    except OSError:
        return False


def delete_media_if_transcribed(settings: Settings, media: Path, transcript: Path, frames_done: bool = True) -> int:
    """Step 1 of the policy. Returns the bytes freed (0 if kept)."""
    if not settings["retention"]["delete_media_after_transcription"]:
        return 0
    if not (frames_done and transcript_readable(transcript)):
        return 0
    return delete_path(settings, media, f"transcribed into {Path(transcript).name}")


# ------------------------------------------------------------ after the analysis


@dataclass
class CleanPlan:
    folder: Path
    ok: bool
    reason: str
    to_delete: list = field(default_factory=list)
    bytes: int = 0
    key_frames: list = field(default_factory=list)


def analysis_complete(folder: Path) -> tuple[bool, str]:
    """The report and the trades CSV exist and can be read back."""
    report, trades = folder / REPORT_NAME, folder / TRADES_NAME
    if not transcript_readable(report):
        return False, f"{REPORT_NAME} missing or empty: nothing will be deleted"
    if not trades.exists():
        return False, f"{TRADES_NAME} missing: nothing will be deleted"
    try:
        with trades.open(encoding="utf-8", newline="") as fh:
            header = next(csv.reader(fh), [])
    except (OSError, ValueError):  # ValueError covers undecodable bytes
        return False, f"{TRADES_NAME} not readable: nothing will be deleted"
    if "trade_id" not in header:
        return False, f"{TRADES_NAME} has no 'trade_id' column: nothing will be deleted"
    return True, "analysis written and read back"


def _all_frames(folder: Path) -> list[Path]:
    frames = []
    for d in FRAME_DIRS:
        if (folder / d).exists():
            frames += sorted(p for p in (folder / d).rglob("*.jpg"))
    return frames


def choose_key_frames(folder: Path, n: int = 6) -> list[Path]:
    """Frames listed in key_frames.txt (written by the analysis), else evenly spaced frames."""
    listed = folder / KEY_FRAMES_LIST
    if listed.exists():
        chosen = []
        for line in listed.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                p = (folder / line) if not Path(line).is_absolute() else Path(line)
                if p.exists():
                    chosen.append(p)
        if chosen:
            return chosen[:6]
    frames = [p for p in _all_frames(folder) if p.parent.name != "sheets" and "sheet" not in p.name]
    if not frames:
        return []
    n = max(1, min(n, len(frames)))
    step = len(frames) / n
    return [frames[int(i * step + step / 2)] for i in range(n)]


def make_key_frames_image(frames: list[Path], out: Path) -> bool:
    """One image with the key frames (Pillow if available, else a folder of copies)."""
    if not frames:
        return False
    try:
        from PIL import Image

        cols = 2 if len(frames) <= 4 else 3
        rows = (len(frames) + cols - 1) // cols
        thumbs = []
        for f in frames:
            im = Image.open(f).convert("RGB")
            im.thumbnail((640, 640))
            thumbs.append(im)
        w = max(t.width for t in thumbs)
        h = max(t.height for t in thumbs)
        sheet = Image.new("RGB", (cols * w, rows * h), "white")
        for i, t in enumerate(thumbs):
            sheet.paste(t, ((i % cols) * w, (i // cols) * h))
        sheet.save(out, quality=85)
        return out.exists()
    except Exception:  # Pillow missing or an unreadable frame: keep plain copies instead
        folder = out.with_suffix("")
        folder.mkdir(exist_ok=True)
        for f in frames:
            shutil.copy2(f, folder / f.name)
        return any(folder.iterdir())


def plan_clean(settings: Settings, folder, keep_media: bool = False) -> CleanPlan:
    folder = Path(folder)
    ok, reason = analysis_complete(folder)
    plan = CleanPlan(folder, ok, reason)
    if not ok:
        return plan
    if keep_media:
        plan.ok, plan.reason = False, "--keep-media: nothing will be deleted"
        return plan
    targets = []
    if settings["retention"]["delete_frames_after_analysis"]:
        targets += [folder / d for d in FRAME_DIRS if (folder / d).exists()]
    targets += [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXT]
    # never touch what must stay
    keep = {folder / REPORT_NAME, folder / TRADES_NAME, folder / KEY_FRAMES_NAME}
    targets = [t for t in targets if t not in keep and not any(t != d and d in t.parents for d in targets)]
    plan.to_delete = targets
    plan.bytes = sum(_size(t) for t in targets)
    plan.key_frames = choose_key_frames(folder, int(settings["retention"]["key_frames"]))
    return plan


def execute_clean(settings: Settings, plan: CleanPlan) -> int:
    """Delete what the plan lists. Saves the key frames first; stops if that fails."""
    if not plan.ok or not plan.to_delete:
        return 0
    key_out = plan.folder / KEY_FRAMES_NAME
    if plan.key_frames and not key_out.exists():
        if not make_key_frames_image(plan.key_frames, key_out):
            return 0  # better keep everything than lose the evidence
    ok, _ = analysis_complete(plan.folder)  # read back again right before deleting
    if not ok:
        return 0
    freed = 0
    for target in plan.to_delete:
        freed += delete_path(settings, target, "analysis complete")
    return freed


def human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} GB"
