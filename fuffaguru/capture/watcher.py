"""The live watcher: every N seconds (60 by default) check every followed profile.

* checking every 5 minutes loses the beginning of a live: the default is 60 s;
* "already recording" is decided PER PROFILE, from the recorder's lock (held
  also between two ffmpeg runs) and from the recorder process itself;
* when a profile is live and free, a recorder process is started for it;
  several lives are recorded at the same time;
* the watcher writes ``data/status.json`` (used by the ``status`` command)
  and checks the free disk space before starting anything.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from .detect import detector_for
from .locks import ProfileLock
from .notify import Notifier
from .profiles import Profile, ProfileStore
from .retention import disk_ok
from .settings import Settings

log = logging.getLogger("goodbye_fuffaguru")


def setup_logging(settings: Settings, name: str) -> None:
    logger = logging.getLogger("goodbye_fuffaguru")
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(settings.logs_dir / f"{name}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)


def spawn_recorder(settings: Settings, profile: Profile) -> subprocess.Popen:
    """Start ``python -m fuffaguru record <key>`` in the background, without a console window."""
    out = (settings.logs_dir / f"record_{profile.platform}_{profile.slug}.log").open("a", encoding="utf-8")
    cmd = [sys.executable, "-m", "fuffaguru", "--root", str(settings.root), "record", profile.key]
    kwargs: dict = {"stdout": out, "stderr": subprocess.STDOUT, "cwd": str(settings.root)}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


class Watcher:
    def __init__(self, settings: Settings, *, store: Optional[ProfileStore] = None,
                 detector_factory: Callable = detector_for, spawn: Optional[Callable] = None,
                 notifier: Optional[Notifier] = None, disk_check: Optional[Callable[[], bool]] = None,
                 clock: Callable[[], float] = time.time, lock_factory: Optional[Callable] = None):
        self.settings = settings
        self.store = store or ProfileStore(settings.data_dir)
        self.detector_factory = detector_factory
        self.spawn = spawn or (lambda p: spawn_recorder(settings, p))
        self.notifier = notifier or Notifier(settings)
        self.disk_check = disk_check or (lambda: disk_ok(settings, self.notifier))
        self.clock = clock
        stale = float(settings["watch"]["stale_lock_seconds"])
        self.lock_factory = lock_factory or (lambda p: ProfileLock(p.folder(settings.data_dir) / "live",
                                                                   stale_seconds=stale, clock=clock))
        self.procs: dict = {}
        self._low_disk_alerted = 0.0

    @property
    def status_path(self) -> Path:
        return self.settings.data_dir / "status.json"

    def _status(self) -> dict:
        try:
            return json.loads(self.status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"profiles": {}}

    def _save_status(self, status: dict) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    def busy(self, profile: Profile) -> bool:
        proc = self.procs.get(profile.key)
        if proc is not None and proc.poll() is None:
            return True
        return self.lock_factory(profile).busy()

    def check_once(self) -> dict:
        """One round over all profiles. Returns {profile key: action}."""
        status = self._status()
        status.setdefault("profiles", {})
        now = _dt.datetime.now().isoformat(timespec="seconds")
        status["watcher_heartbeat"] = now
        actions = {}
        for profile in self.store.all():
            entry = status["profiles"].setdefault(profile.key, {})
            if self.busy(profile):
                actions[profile.key] = "busy"
                entry.update(last_check=now, state="recording")
                continue
            try:
                st = self.detector_factory(profile, self.settings).check(profile)
            except Exception as exc:
                actions[profile.key] = "error"
                entry.update(last_check=now, state="error", last_error=f"{now} {exc}")
                log.warning("[%s] check failed: %s", profile.key, exc)
                continue
            entry.update(last_check=now, state="live" if st.live else "idle", reason=st.reason)
            if not st.live:
                actions[profile.key] = "idle"
                continue
            if not self.disk_check():
                actions[profile.key] = "low_disk"
                entry["last_error"] = f"{now} live not recorded: low disk space"
                continue
            self.procs[profile.key] = self.spawn(profile)
            entry["last_live_start"] = now
            actions[profile.key] = "started"
            log.info("[%s] live detected (%s): recorder started", profile.key, st.reason)
        self._save_status(status)
        return actions

    def run_forever(self, interval: Optional[float] = None, sleep: Callable[[float], None] = time.sleep) -> None:
        interval = float(interval or self.settings["watch"]["interval_seconds"])
        log.info("watcher started: %d profiles, every %.0f s", len(self.store.all()), interval)
        while True:
            try:
                self.check_once()
            except Exception as exc:  # never die: log and continue
                log.exception("watcher round failed: %s", exc)
            sleep(interval)
