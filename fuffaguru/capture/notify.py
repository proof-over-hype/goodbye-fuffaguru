"""Alerts to the user: always in the log, optionally on the desktop and on Telegram.

Silence is the worst failure of a watcher: if a live is on and nothing is
being recorded, the user must know while there is still time to act.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import platform
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from .settings import Settings

log = logging.getLogger("goodbye_fuffaguru")


class Notifier:
    def __init__(self, settings: Settings, sender: Optional[Callable[[str, str], None]] = None):
        self.settings = settings
        self.sender = sender  # tests can inject a fake
        self.sent: list[tuple[str, str]] = []

    @property
    def alerts_log(self) -> Path:
        return self.settings.logs_dir / "alerts.log"

    def alert(self, title: str, message: str) -> None:
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.alerts_log.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} ALERT {title}: {message}\n")
        log.warning("ALERT %s: %s", title, message)
        self.sent.append((title, message))
        if self.sender:
            self.sender(title, message)
            return
        cfg = self.settings["notify"]
        if cfg.get("desktop"):
            _desktop(title, message)
        if cfg.get("telegram"):
            _telegram(cfg, title, message)


def _desktop(title: str, message: str) -> None:
    try:
        try:
            from plyer import notification  # optional
            notification.notify(title=title, message=message[:250], app_name="Goodbye FuffaGuru")
            return
        except ImportError:
            pass
        system = platform.system()
        if system == "Darwin":
            script = f'display notification {json.dumps(message)} with title {json.dumps(title)}'
            subprocess.run(["osascript", "-e", script], timeout=10)
        elif system == "Linux" and shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message], timeout=10)
        elif system == "Windows":
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null;"
                "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                "$x=$t.GetElementsByTagName('text');"
                f"$x.Item(0).AppendChild($t.CreateTextNode({json.dumps(title)})) > $null;"
                f"$x.Item(1).AppendChild($t.CreateTextNode({json.dumps(message[:250])})) > $null;"
                "$id='{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id).Show("
                "[Windows.UI.Notifications.ToastNotification]::new($t))"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=20, capture_output=True)
    except Exception as exc:  # a failed notification must never stop a recording
        log.warning("desktop notification failed: %s", exc)


def _telegram(cfg: dict, title: str, message: str) -> None:
    token = os.environ.get(cfg.get("telegram_token_env", ""), "")
    chat = os.environ.get(cfg.get("telegram_chat_env", ""), "")
    if not token or not chat:
        log.warning("telegram enabled but token/chat environment variables are not set")
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": f"{title}\n{message}"}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=15)
    except Exception as exc:
        log.warning("telegram notification failed: %s", exc)
