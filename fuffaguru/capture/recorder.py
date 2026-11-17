"""Record one live session in 3-minute pieces, without losing it.

Lessons built into this loop:

* the signed address of a live stream EXPIRES and ffmpeg stops. When ffmpeg
  exits, the recorder reads a fresh address and continues IN THE SAME session
  folder. It closes the session only after ``end_checks`` consecutive "not
  live" answers (3 checks one minute apart by default). Only then it writes
  ``END`` and the transcript is closed. One live = one folder.
* the per-profile lock is held for the whole session, also while waiting
  between two ffmpeg runs, so the watcher never starts a second recorder for
  the same profile, while other profiles can be recorded at the same time.
* if the page says "live" but no valid stream is found for ``K`` checks in a
  row, the user is ALERTED (log + optional desktop/Telegram) instead of the
  recorder staying silent.
* pieces are transcribed while the live goes on; each piece is deleted once
  transcribed and its frames extracted (retention policy).
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from ..transcribe import format_timestamp, load_segments
from . import ytdlp
from .cookies import USER_AGENT, ytdlp_cookie_args
from .detect import Detector, LiveStatus, detector_for, has_video_and_audio
from .locks import ProfileLock
from .notify import Notifier
from .process import MediaProcessor
from .profiles import Profile
from .retention import MEDIA_EXT, disk_ok
from .settings import Settings

log = logging.getLogger("goodbye_fuffaguru")
PART_TIME = re.compile(r"part_(\d{8})-(\d{6})")


def ffmpeg_segment_cmd(url: str, parts_dir: Path, run_idx: int, segment_seconds: int, platform: str,
                       ffmpeg: str = "ffmpeg") -> list[str]:
    """ffmpeg command: copy the stream into pieces named by their start time (local clock)."""
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-nostdin", "-rw_timeout", "15000000"]
    if platform == "tiktok":
        cmd += ["-user_agent", USER_AGENT, "-headers", "Referer: https://www.tiktok.com/\r\n"]
    cmd += ["-i", url, "-map", "0:v:0?", "-map", "0:a:0?", "-c", "copy",
            "-f", "segment", "-segment_time", str(int(segment_seconds)), "-reset_timestamps", "1",
            "-strftime", "1", str(Path(parts_dir) / f"part_%Y%m%d-%H%M%S_r{run_idx:02d}.ts")]
    return cmd


class PartProcessor:
    """Transcribes finished pieces while the live goes on, and at the end all of them."""

    def __init__(self, session_dir: Path, processor: Optional[MediaProcessor]):
        self.session = Path(session_dir)
        self.parts = self.session / "parts"
        self.processor = processor
        self.done: set[str] = set()
        self.disabled = processor is None
        self.lock = threading.Lock()

    def pending(self, final: bool) -> list[Path]:
        media = sorted(p for p in self.parts.glob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXT
                       and p.suffix.lower() != ".part")
        ready = media if final else media[:-1]  # the newest piece may still be written
        return [p for p in ready if p.name not in self.done]

    def step(self, final: bool = False) -> int:
        if self.disabled:
            return 0
        n = 0
        with self.lock:
            for part in self.pending(final):
                try:
                    self.processor.process(part, self.session, name=part.stem)
                except ImportError as exc:
                    log.warning("transcription unavailable (%s): pieces are kept", exc)
                    self.disabled = True
                    break
                except Exception as exc:
                    log.warning("could not process %s: %s", part.name, exc)
                self.done.add(part.name)
                n += 1
            if n:
                self.rebuild_transcript()
        return n

    def rebuild_transcript(self) -> Path:
        """One transcript.md for the whole session, with clock times."""
        lines = [f"# Live transcript - {self.session.name}", ""]
        for js in sorted((self.session / "transcript").glob("part_*.json")):
            m = PART_TIME.search(js.stem)
            start = _dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S") if m else None
            lines.append(f"## {js.stem}")
            for s in load_segments(js):
                stamp = (start + _dt.timedelta(seconds=s.start)).strftime("%H:%M:%S") if start else format_timestamp(s.start)
                lines.append(f"[{stamp}] {s.text}")
            lines.append("")
        out = self.session / "transcript.md"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out


class LiveRecorder:
    def __init__(
        self,
        profile: Profile,
        settings: Settings,
        detector: Optional[Detector] = None,
        *,
        runner: Optional[Callable[[str, Path, int], int]] = None,
        probe: Optional[Callable[[str], bool]] = None,
        notifier: Optional[Notifier] = None,
        processor: Optional[MediaProcessor] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        lock: Optional[ProfileLock] = None,
        disk_check: Optional[Callable[[], bool]] = None,
        live_processing: bool = True,
    ):
        self.profile = profile
        self.settings = settings
        self.w = settings["watch"]
        self.detector = detector or detector_for(profile, settings)
        self.runner = runner or self._run_ffmpeg
        self.probe = probe or has_video_and_audio
        self.notifier = notifier or Notifier(settings)
        self.processor = processor
        self._sleep_fn = sleep
        self.clock = clock
        self.live_dir = profile.folder(settings.data_dir) / "live"
        self.lock = lock or ProfileLock(self.live_dir, stale_seconds=float(self.w["stale_lock_seconds"]), clock=clock)
        self.disk_check = disk_check or (lambda: disk_ok(settings, self.notifier))
        self.live_processing = live_processing
        self.session: Optional[Path] = None
        self.state: dict = {}

    # ------------------------------------------------------------ bookkeeping
    def event(self, text: str) -> None:
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.info("[%s] %s", self.profile.key, text)
        if self.session:
            with (self.session / "events.log").open("a", encoding="utf-8") as fh:
                fh.write(f"{stamp} {text}\n")

    def save_state(self, **kw) -> None:
        self.state.update(kw)
        if self.session:
            (self.session / "session.json").write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        self.lock.heartbeat(state=self.state.get("state"))

    def sleep(self, seconds: float) -> None:
        """Sleep in short steps, keeping the lock alive (the pause counts as 'recording')."""
        remaining = float(seconds)
        while remaining > 0:
            step = min(15.0, remaining)
            self.lock.heartbeat(state="waiting")
            self._sleep_fn(step)
            remaining -= step
        self.lock.heartbeat(state="waiting")

    # ------------------------------------------------------------- recording
    def _run_ffmpeg(self, url: str, parts_dir: Path, run_idx: int) -> int:
        if self.profile.platform == "youtube" and self.w.get("youtube_live_from_start"):
            cmd = ytdlp.live_from_start_cmd(self.profile.live_url, str(parts_dir / f"full_r{run_idx:02d}.%(ext)s"),
                                            ytdlp_cookie_args(self.settings),
                                            self.settings["download"]["max_height"], base=ytdlp.ytdlp_base())
        else:
            cmd = ffmpeg_segment_cmd(url, parts_dir, run_idx, int(self.w["segment_seconds"]), self.profile.platform,
                                     ffmpeg=shutil.which("ffmpeg") or "ffmpeg")
        flags = 0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0  # no console window on Windows
        with (self.session / "ffmpeg.log").open("a", encoding="utf-8") as err:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=err, creationflags=flags)
            while proc.poll() is None:
                self.lock.heartbeat(state="recording")
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    pass
        return proc.returncode

    def run(self) -> Optional[Path]:
        if not self.lock.acquire():
            log.info("[%s] already being recorded", self.profile.key)
            return None
        worker = None
        stop = threading.Event()
        try:
            started = _dt.datetime.now()
            self.session = self.live_dir / started.strftime("%Y%m%d_%H%M%S")
            parts = self.session / "parts"
            parts.mkdir(parents=True, exist_ok=True)
            self.lock.heartbeat(state="starting", session=self.session.name)
            self.save_state(profile=self.profile.key, state="recording", started=started.isoformat(timespec="seconds"),
                            ffmpeg_runs=0, alerts=0)
            pp = PartProcessor(self.session, self.processor)
            if self.live_processing and self.processor is not None:
                def loop():
                    while not stop.wait(20):
                        pp.step(final=False)
                worker = threading.Thread(target=loop, daemon=True)
                worker.start()

            end_checks = int(self.w["end_checks"])
            alert_after = int(self.w["stream_missing_alert_after"])
            negatives = missing = runs = 0
            alerted = False
            while True:
                self.lock.heartbeat(state="checking")
                if not self.disk_check():
                    self.event("stopped: disk space below the minimum")
                    self.save_state(state="stopped_low_disk")
                    break
                st: LiveStatus = self.detector.check(self.profile)
                if st.live and st.stream_url and self.probe(st.stream_url):
                    negatives = missing = 0
                    alerted = False
                    runs += 1
                    self.event(f"ffmpeg run {runs} starts ({st.reason})")
                    self.save_state(ffmpeg_runs=runs, state="recording")
                    t0 = self.clock()
                    code = self.runner(st.stream_url, parts, runs)
                    lasted = self.clock() - t0
                    self.event(f"ffmpeg run {runs} ended (code {code}, {lasted:.0f} s): reading a new address")
                    if lasted < 10:
                        missing += 1
                        self.sleep(float(self.w["retry_seconds"]))
                    continue
                if st.live:
                    missing += 1
                    negatives = 0
                    why = st.reason if not st.stream_url else "stream without both video and audio"
                    self.event(f"live but no usable stream ({why}), check {missing}")
                    if missing >= alert_after and not alerted:
                        self.notifier.alert(
                            f"Live not being recorded: {self.profile.key}",
                            f"The page says live but no valid stream was found for {missing} checks ({why}). "
                            "Open the live in your browser, check your cookies (setup), update yt-dlp.")
                        alerted = True
                        self.save_state(alerts=self.state.get("alerts", 0) + 1)
                    self.sleep(float(self.w["retry_seconds"]))
                    continue
                negatives += 1
                self.event(f"not live ({st.reason}), check {negatives} of {end_checks}")
                if negatives >= end_checks:
                    break
                self.sleep(float(self.w["end_check_interval_seconds"]))

            ended = _dt.datetime.now().isoformat(timespec="seconds")
            (self.session / "END").write_text(ended + "\n", encoding="utf-8")
            if self.state.get("state") == "recording":
                self.state["state"] = "ended"
            self.save_state(ended=ended)
            self.event("session closed")
            stop.set()
            if worker:
                worker.join(timeout=5)
            pp.step(final=True)
            if not (self.session / "transcript.md").exists():
                pp.rebuild_transcript()
            self.save_state(transcript="transcript.md")
            return self.session
        finally:
            stop.set()
            self.lock.release()
