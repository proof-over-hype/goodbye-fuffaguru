"""Speech to text with timestamps, using faster-whisper (optional dependency).

Install with ``pip install faster-whisper``. The model is downloaded by
faster-whisper itself the first time it is used. On a CPU the "small" model is
a good compromise; "large-v3" is much better on trading jargon but slow.

Tips from experience:

* automatic transcripts mangle jargon (CHOCH, doji, instrument names): check
  instruments and numbers on the video frames, never on the text alone;
* keep the timestamps: every claim, rule or trade you extract must point back
  to the second where it was said.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class Segment:
    start: float
    end: float
    text: str


def format_timestamp(seconds: float, srt: bool = False) -> str:
    """12.5 -> '00:00:12' (or '00:00:12,500' for SRT)."""
    seconds = max(0.0, float(seconds))
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}" if srt else f"{h:02d}:{m:02d}:{s:02d}"


def _load_model(model_size: str, device: str, compute_type: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ImportError(
            "faster-whisper is not installed. Install it with: pip install faster-whisper"
        ) from exc
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe(
    media_path,
    *,
    model_size: str = "small",
    language: Optional[str] = None,
    device: str = "auto",
    compute_type: str = "default",
    vad_filter: bool = True,
    model=None,
) -> list[Segment]:
    """Transcribe an audio or video file and return timestamped segments.

    ``model`` lets you reuse an already loaded WhisperModel (useful for many files).
    """
    media_path = Path(media_path)
    if not media_path.exists():
        raise FileNotFoundError(media_path)
    model = model or _load_model(model_size, device, compute_type)
    segments, _info = model.transcribe(str(media_path), language=language, vad_filter=vad_filter)
    return [Segment(float(s.start), float(s.end), s.text.strip()) for s in segments]


def segments_to_markdown(segments: Iterable[Segment], title: str = "", offset: float = 0.0) -> str:
    lines = [f"# {title}", ""] if title else []
    for s in segments:
        lines.append(f"[{format_timestamp(s.start + offset)}] {s.text}")
    return "\n".join(lines) + "\n"


def segments_to_srt(segments: Iterable[Segment], offset: float = 0.0) -> str:
    out = []
    for i, s in enumerate(segments, start=1):
        out.append(str(i))
        out.append(f"{format_timestamp(s.start + offset, srt=True)} --> {format_timestamp(s.end + offset, srt=True)}")
        out.append(s.text)
        out.append("")
    return "\n".join(out)


def save_transcript(segments: list[Segment], path, title: str = "") -> Path:
    """Save as .md (default), .srt or .json depending on the extension."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".srt":
        path.write_text(segments_to_srt(segments), encoding="utf-8")
    elif suffix == ".json":
        path.write_text(json.dumps([asdict(s) for s in segments], ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        path.write_text(segments_to_markdown(segments, title=title), encoding="utf-8")
    return path


def load_segments(path) -> list[Segment]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Segment(float(d["start"]), float(d["end"]), d["text"]) for d in data]
