"""Turn a media file into text and frames, then (by default) delete the media."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from .. import frames as frames_mod
from ..transcribe import Segment, save_transcript, transcribe
from .retention import delete_media_if_transcribed
from .settings import Settings

log = logging.getLogger("goodbye_fuffaguru")


class MediaProcessor:
    """transcribe -> frames + contact sheets -> delete the media (policy permitting).

    ``transcribe_fn(path) -> list[Segment]`` and ``frames_fn(path, frames_dir, sheets_dir)``
    can be replaced (tests, other engines).
    """

    def __init__(self, settings: Settings, transcribe_fn: Optional[Callable] = None,
                 frames_fn: Optional[Callable] = None):
        self.settings = settings
        self._model = None
        self.transcribe_fn = transcribe_fn or self._whisper
        self.frames_fn = frames_fn or self._ffmpeg_frames

    def _whisper(self, path: Path) -> list[Segment]:
        t = self.settings["transcription"]
        if self._model is None:
            from ..transcribe import _load_model
            self._model = _load_model(t["model"], t["device"], t["compute_type"])
        return transcribe(path, language=t["language"], model=self._model)

    def _ffmpeg_frames(self, path: Path, frames_dir: Path, sheets_dir: Path) -> None:
        f = self.settings["frames"]
        frames_mod.extract_frames(path, frames_dir, every_seconds=float(f["every_seconds"]))
        frames_mod.contact_sheet(path, sheets_dir / "sheet_%03d.jpg", every_seconds=float(f["sheet_every_seconds"]),
                                 cols=int(f["sheet_cols"]), rows=int(f["sheet_rows"]))

    def process(self, media: Path, out_dir: Path, name: Optional[str] = None) -> dict:
        """Returns {'segments', 'transcript', 'frames_ok', 'deleted_bytes'}."""
        media, out_dir = Path(media), Path(out_dir)
        name = name or media.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        tdir = out_dir / "transcript"
        segs = self.transcribe_fn(media)
        save_transcript(segs, tdir / f"{name}.json")
        md = save_transcript(segs, tdir / f"{name}.md", title=name)
        frames_ok = True
        try:
            self.frames_fn(media, out_dir / "frames" / name, out_dir / "sheets" / name)
        except Exception as exc:
            frames_ok = False
            log.warning("frames failed for %s: %s (media kept)", media.name, exc)
        freed = delete_media_if_transcribed(self.settings, media, md, frames_done=frames_ok)
        return {"segments": segs, "transcript": md, "frames_ok": frames_ok, "deleted_bytes": freed}
