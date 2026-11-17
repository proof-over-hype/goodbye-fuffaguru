"""One lock per profile: "I am already recording this profile".

The lock is held by the recorder for the *whole* live session, including the
pauses between two ffmpeg runs (when the signed address expired and a new one
is being read). Because it is per profile, several lives can be recorded at
the same time.

A lock is considered alive when its process is running and its heartbeat is
recent; otherwise it is stale and can be taken over.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable, Optional


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class ProfileLock:
    def __init__(self, folder, stale_seconds: float = 600, clock: Callable[[], float] = time.time,
                 is_alive: Callable[[int], bool] = pid_alive, pid: Optional[int] = None):
        self.path = Path(folder) / ".recording.lock"
        self.stale_seconds = stale_seconds
        self.clock = clock
        self.is_alive = is_alive
        self.pid = pid if pid is not None else os.getpid()
        self.held = False

    def read(self) -> Optional[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def busy(self) -> bool:
        """True if *someone* (this or another process) is recording this profile."""
        info = self.read()
        if not info:
            return False
        fresh = self.clock() - float(info.get("heartbeat", 0)) < self.stale_seconds
        return fresh and self.is_alive(int(info.get("pid", -1)))

    def acquire(self, session: str = "") -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.busy():
            return False
        if self.path.exists():
            self.path.unlink()  # stale
        payload = {"pid": self.pid, "session": session, "started": self.clock(), "heartbeat": self.clock(),
                   "state": "starting"}
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        self.held = True
        return True

    def heartbeat(self, state: Optional[str] = None, session: Optional[str] = None) -> None:
        if not self.held:
            return
        info = self.read() or {"pid": self.pid, "started": self.clock()}
        info["heartbeat"] = self.clock()
        if state:
            info["state"] = state
        if session is not None:
            info["session"] = session
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(info), encoding="utf-8")
        os.replace(tmp, self.path)

    def release(self) -> None:
        if self.held and self.path.exists():
            self.path.unlink()
        self.held = False
