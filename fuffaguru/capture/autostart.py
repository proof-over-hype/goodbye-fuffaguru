"""Start the watcher again by itself after a reboot.

* Windows: a Task Scheduler task "at log on" (``schtasks``), with pythonw so
  no console window appears;
* macOS: a LaunchAgent in ~/Library/LaunchAgents (``launchctl``);
* Linux: an ``@reboot`` line in the user's crontab.

``install_autostart(dry_run=True)`` only prints what it would do. Nothing
here runs unless the user asks for it.
"""

from __future__ import annotations

import platform
import shlex
import subprocess
import sys
from pathlib import Path

TASK_NAME = "GoodbyeFuffaGuruWatcher"
PLIST_LABEL = "org.goodbye-fuffaguru.watcher"


def _pythonw(python: str) -> str:
    p = Path(python)
    candidate = p.with_name("pythonw.exe")
    return str(candidate) if candidate.exists() else str(p)


def windows_commands(root: Path, python: str) -> list[list[str]]:
    action = f'"{_pythonw(python)}" -m fuffaguru --root "{root}" watch'
    return [["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/RL", "LIMITED", "/TN", TASK_NAME, "/TR", action]]


def windows_uninstall() -> list[list[str]]:
    return [["schtasks", "/Delete", "/F", "/TN", TASK_NAME]]


def mac_plist(root: Path, python: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{PLIST_LABEL}</string>
  <key>ProgramArguments</key><array>
    <string>{python}</string><string>-m</string><string>fuffaguru</string>
    <string>--root</string><string>{root}</string><string>watch</string>
  </array>
  <key>WorkingDirectory</key><string>{root}</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{root}/data/logs/launchd.log</string>
  <key>StandardErrorPath</key><string>{root}/data/logs/launchd.log</string>
</dict></plist>
"""


def cron_line(root: Path, python: str) -> str:
    r, py = shlex.quote(str(root)), shlex.quote(python)
    return f"@reboot cd {r} && {py} -m fuffaguru --root {r} watch >> {r}/data/logs/cron.log 2>&1"


def install_autostart(root, python: str = sys.executable, dry_run: bool = False, system: str = None) -> list[str]:
    """Install the autostart for this system. Returns a description of each step."""
    root = Path(root).resolve()
    system = system or platform.system()
    steps = []
    if system == "Windows":
        for cmd in windows_commands(root, python):
            steps.append(subprocess.list2cmdline(cmd))
            if not dry_run:
                subprocess.run(cmd, check=True)
    elif system == "Darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
        steps.append(f"write {plist}")
        steps.append(f"launchctl load -w {plist}")
        if not dry_run:
            plist.parent.mkdir(parents=True, exist_ok=True)
            plist.write_text(mac_plist(root, python), encoding="utf-8")
            subprocess.run(["launchctl", "load", "-w", str(plist)], check=True)
    else:
        line = cron_line(root, python)
        steps.append(f"add to crontab: {line}")
        if not dry_run:
            current = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
            if line not in current:
                new = (current.rstrip("\n") + "\n" if current.strip() else "") + line + "\n"
                subprocess.run(["crontab", "-"], input=new, text=True, check=True)
    return steps


def uninstall_autostart(dry_run: bool = False, system: str = None) -> list[str]:
    system = system or platform.system()
    steps = []
    if system == "Windows":
        for cmd in windows_uninstall():
            steps.append(subprocess.list2cmdline(cmd))
            if not dry_run:
                subprocess.run(cmd)
    elif system == "Darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
        steps.append(f"launchctl unload -w {plist} and delete it")
        if not dry_run and plist.exists():
            subprocess.run(["launchctl", "unload", "-w", str(plist)])
            plist.unlink()
    else:
        steps.append("remove the '-m fuffaguru ... watch' line from crontab")
        if not dry_run:
            current = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
            kept = "\n".join(ln for ln in current.splitlines() if "-m fuffaguru" not in ln)
            subprocess.run(["crontab", "-"], input=kept + "\n", text=True)
    return steps
