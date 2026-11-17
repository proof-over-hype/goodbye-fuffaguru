"""The ``status`` command: followed profiles, recordings in progress, last lives, errors, disk."""

from __future__ import annotations

import json
from pathlib import Path

from .locks import ProfileLock
from .profiles import ProfileStore
from .retention import REPORT_NAME, free_gb
from .settings import Settings


def _tail(path: Path, n: int) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-n:]


def sessions(folder: Path) -> list[dict]:
    out = []
    live = folder / "live"
    if not live.exists():
        return out
    for d in sorted((p for p in live.iterdir() if p.is_dir()), reverse=True):
        info = {}
        try:
            info = json.loads((d / "session.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        out.append({
            "session": d.name,
            "state": info.get("state", "?"),
            "ffmpeg_runs": info.get("ffmpeg_runs", 0),
            "pieces_left": len(list((d / "parts").glob("*"))) if (d / "parts").exists() else 0,
            "transcribed": len(list((d / "transcript").glob("*.json"))) if (d / "transcript").exists() else 0,
            "analysed": (d / REPORT_NAME).exists(),
            "alerts": info.get("alerts", 0),
        })
    return out


def status_text(settings: Settings, last: int = 3) -> str:
    store = ProfileStore(settings.data_dir)
    profiles = store.all()
    try:
        watcher = json.loads((settings.data_dir / "status.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        watcher = {"profiles": {}}
    lines = ["Goodbye FuffaGuru - status", ""]
    lines.append(f"Watcher last round: {watcher.get('watcher_heartbeat', 'never (is the watcher running?)')}")
    try:
        lines.append(f"Free disk space: {free_gb(settings.data_dir):.1f} GB "
                     f"(minimum {settings['retention']['min_free_gb']} GB)")
    except OSError:
        pass
    lines.append("")
    if not profiles:
        lines.append("No profiles followed yet: use 'follow <url or @handle>'.")
    for p in profiles:
        folder = p.folder(settings.data_dir)
        busy = ProfileLock(folder / "live", stale_seconds=float(settings["watch"]["stale_lock_seconds"])).busy()
        w = watcher.get("profiles", {}).get(p.key, {})
        lines.append(f"* {p.key}  {'RECORDING NOW' if busy else w.get('state', 'not checked yet')}"
                     f"  (last check {w.get('last_check', '-')})")
        if w.get("last_error"):
            lines.append(f"    last error: {w['last_error']}")
        hist = folder / "history"
        if hist.exists():
            n = sum(1 for d in hist.iterdir() if d.is_dir())
            lines.append(f"    history: {n} items")
        for s in sessions(folder)[:last]:
            lines.append(f"    live {s['session']}: {s['state']}, ffmpeg runs {s['ffmpeg_runs']}, "
                         f"transcribed pieces {s['transcribed']}, pieces on disk {s['pieces_left']}, "
                         f"analysed {'yes' if s['analysed'] else 'no'}"
                         + (f", ALERTS {s['alerts']}" if s['alerts'] else ""))
    alerts = _tail(settings.logs_dir / "alerts.log", 5)
    if alerts:
        lines += ["", "Last alerts:"] + [f"  {a}" for a in alerts]
    errors = [ln for ln in _tail(settings.logs_dir / "watcher.log", 200) if " ERROR " in ln or " WARNING " in ln][-5:]
    if errors:
        lines += ["", "Last warnings and errors of the watcher:"] + [f"  {e}" for e in errors]
    return "\n".join(lines) + "\n"
