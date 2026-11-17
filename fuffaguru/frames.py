"""Frames and contact sheets from a video with ffmpeg (must be on PATH).

Charts carry the information that transcripts miss: the instrument, the
timeframe, the price axis, the position box with entry, stop and target. A
frame every 2 seconds is enough to read a 1-minute chart; contact sheets
(a grid of small frames) let you find the interesting minutes fast.

The command builders are pure functions, so they can be tested and printed
without running anything.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence


def ffmpeg_path() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise FileNotFoundError("ffmpeg not found on PATH: install it from https://ffmpeg.org/")
    return exe


def build_frames_cmd(video, out_dir, every_seconds: float = 2.0, width: Optional[int] = None,
                     ffmpeg: str = "ffmpeg", pattern: str = "frame_%06d.jpg") -> list[str]:
    """ffmpeg command that saves one frame every ``every_seconds`` seconds."""
    if every_seconds <= 0:
        raise ValueError("every_seconds must be positive")
    vf = f"fps=1/{every_seconds:g}"
    if width:
        vf += f",scale={int(width)}:-2"
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
            "-vf", vf, "-q:v", "3", str(Path(out_dir) / pattern)]


def build_frame_at_cmd(video, seconds: float, out_path, ffmpeg: str = "ffmpeg") -> list[str]:
    """ffmpeg command that saves the single frame at ``seconds``."""
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{max(0.0, seconds):.3f}",
            "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out_path)]


def build_contact_sheet_cmd(video, out_path, every_seconds: float = 10.0, cols: int = 4, rows: int = 4,
                            width: int = 320, ffmpeg: str = "ffmpeg") -> list[str]:
    """ffmpeg command that writes grids of cols x rows frames (one image per grid).

    Use a pattern such as ``sheet_%03d.jpg`` in ``out_path`` for long videos.
    """
    vf = f"fps=1/{every_seconds:g},scale={int(width)}:-2,tile={int(cols)}x{int(rows)}"
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
            "-vf", vf, "-q:v", "3", str(out_path)]


def frame_time(index: int, every_seconds: float) -> float:
    """Approximate time in the video of frame number ``index`` (1-based) written by ``extract_frames``."""
    return (index - 1) * every_seconds + every_seconds / 2.0


def _run(cmd: Sequence[str]) -> None:
    proc = subprocess.run(list(cmd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {proc.stderr.strip()[:500]}")


def extract_frames(video, out_dir, every_seconds: float = 2.0, width: Optional[int] = None) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _run(build_frames_cmd(video, out_dir, every_seconds, width, ffmpeg=ffmpeg_path()))
    return sorted(out_dir.glob("frame_*.jpg"))


def extract_frame_at(video, seconds: float, out_path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(build_frame_at_cmd(video, seconds, out_path, ffmpeg=ffmpeg_path()))
    return out_path


def contact_sheet(video, out_path, every_seconds: float = 10.0, cols: int = 4, rows: int = 4,
                  width: int = 320) -> list[Path]:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(build_contact_sheet_cmd(video, out_path, every_seconds, cols, rows, width, ffmpeg=ffmpeg_path()))
    if "%" in out_path.name:
        prefix = out_path.name.split("%")[0]
        return sorted(out_path.parent.glob(prefix + "*"))
    return [out_path]
