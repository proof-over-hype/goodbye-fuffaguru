"""Command line: ``python -m fuffaguru <command>`` (or ``fuffaguru <command>`` once installed).

Analysis:  transcribe, frames, sheet, verify, freeze, check-freeze
Capture:   setup, follow, unfollow, profiles, history, check-live, watch, record,
           status, process, clean, install-autostart, uninstall-autostart
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__


# ------------------------------------------------------------------- analysis


def cmd_transcribe(a, s):
    from .transcribe import save_transcript, transcribe
    segs = transcribe(a.media, model_size=a.model, language=a.language)
    out = Path(a.out or Path(a.media).with_suffix(".md"))
    save_transcript(segs, out, title=Path(a.media).name)
    save_transcript(segs, out.with_suffix(".json"))
    print(f"{len(segs)} segments -> {out}")


def cmd_frames(a, s):
    from .frames import extract_frames
    files = extract_frames(a.video, a.out_dir, every_seconds=a.every, width=a.width)
    print(f"{len(files)} frames -> {a.out_dir}")


def cmd_sheet(a, s):
    from .frames import contact_sheet
    files = contact_sheet(a.video, a.out, every_seconds=a.every, cols=a.cols, rows=a.rows)
    print(f"{len(files)} contact sheet(s): {', '.join(str(f) for f in files[:3])}")


def cmd_verify(a, s):
    from .report import Claims, reality_check
    from .trades import read_bars, read_trades, validate_bars, validate_trades, verify_trades
    trades = read_trades(a.trades)
    problems = validate_trades(trades)
    bars = read_bars(a.bars)
    problems += validate_bars(bars)
    for p in problems:
        print(f"warning: {p}")
    res = verify_trades(trades, bars, max_minutes=a.max_minutes, target_r=a.target_r, cost=a.cost,
                        entry_bar=a.entry_bar, breakeven_at_r=a.breakeven_at_r, price_tolerance=a.tolerance)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(out, index=False)
    claims = None
    if a.claimed_win_rate is not None or a.claimed_trades_per_week is not None:
        claims = Claims(win_rate=a.claimed_win_rate, win_rate_basis=a.claimed_basis,
                        trades_per_week=a.claimed_trades_per_week)
    rc = reality_check(res, title=a.title, claims=claims, n_trials=a.trials, n_sims=a.sims,
                       min_trades=a.min_trades)
    rc.write(a.report)
    print(f"{len(res)} trades verified -> {out}\nVerdict: {rc.verdict}\nReport -> {a.report}")


def cmd_freeze(a, s):
    from .prereg import freeze_file, missing_recommended
    frozen = freeze_file(a.recipe, a.out)
    miss = missing_recommended(frozen["recipe"])
    if miss:
        print(f"note: recommended keys missing: {', '.join(miss)}")
    print(f"frozen: sha256 {frozen['frozen']['sha256']} at {frozen['frozen']['frozen_at_utc']}")


def cmd_check_freeze(a, s):
    from .prereg import verify_frozen
    ok, msg = verify_frozen(a.frozen)
    print(msg)
    return 0 if ok else 1


# -------------------------------------------------------------------- capture


def _profile(s, key: str):
    from .capture.profiles import ProfileStore, parse_profile
    store = ProfileStore(s.data_dir)
    p = store.get(key)
    if p is None and ":" not in key:
        matches = [x for x in store.all() if x.handle == key.lstrip("@")]
        p = matches[0] if len(matches) == 1 else None
    if p is None:
        try:
            p = parse_profile(key)
        except ValueError:
            raise SystemExit(f"unknown profile {key!r}: use 'profiles' to list them, or 'follow' to add one")
    return p


def cmd_setup(a, s):
    from .capture.setup_wizard import run_setup
    run_setup(s, browser=a.browser, interactive=not a.non_interactive)


def cmd_follow(a, s):
    from .capture.profiles import ProfileStore, parse_profile
    p = ProfileStore(s.data_dir).add(parse_profile(a.target, a.platform))
    print(f"following {p.key} (live page: {p.live_url})")
    if a.history:
        a.key, a.since, a.keep_media, a.urls = p.key, None, False, None
        cmd_history(a, s)


def cmd_unfollow(a, s):
    from .capture.profiles import ProfileStore
    key = _profile(s, a.key).key
    print("removed" if ProfileStore(s.data_dir).remove(key) else "not followed", key)


def cmd_profiles(a, s):
    from .capture.profiles import ProfileStore
    for p in ProfileStore(s.data_dir).all():
        print(f"{p.key}\t{p.page_url}\tadded {p.added_utc}")


def cmd_history(a, s):
    from .capture.history import download_history
    from .capture.watcher import setup_logging
    setup_logging(s, "history")
    urls = Path(a.urls).read_text(encoding="utf-8").split() if a.urls else None
    res = download_history(_profile(s, a.key), s, limit=a.limit, date_after=a.since, keep_media=a.keep_media,
                           urls=urls)
    print(json.dumps(res, indent=2))


def cmd_check_live(a, s):
    from .capture.detect import detector_for, has_video_and_audio
    p = _profile(s, a.key)
    st = detector_for(p, s).check(p)
    print(f"{p.key}: live={st.live} reason={st.reason}")
    if st.stream_url:
        print("stream found; video+audio:", has_video_and_audio(st.stream_url))


def _watcher_pid_file(s) -> Path:
    return s.data_dir / "watcher.pid"


def cmd_watch(a, s):
    from .capture.locks import pid_alive
    from .capture.watcher import Watcher, setup_logging
    pid_file = _watcher_pid_file(s)
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
        except ValueError:
            pid = -1
        if pid_alive(pid) and pid != os.getpid():
            print(f"a watcher is already running (pid {pid})")
            return 0
    if a.background:
        cmd = [sys.executable, "-m", "fuffaguru", "--root", str(s.root), "watch"]
        kw = {"cwd": str(s.root), "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform.startswith("win"):
            kw["creationflags"] = 0x08000000 | 0x00000008  # no window, detached
        else:
            kw["start_new_session"] = True
        proc = subprocess.Popen(cmd, **kw)
        print(f"watcher started in the background (pid {proc.pid}); logs in data/logs/watcher.log")
        return 0
    s.data_dir.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))
    setup_logging(s, "watcher")
    Watcher(s).run_forever(a.interval)


def cmd_record(a, s):
    from .capture.process import MediaProcessor
    from .capture.recorder import LiveRecorder
    from .capture.watcher import setup_logging
    setup_logging(s, "recorder")
    session = LiveRecorder(_profile(s, a.key), s, processor=MediaProcessor(s)).run()
    print(f"session: {session}" if session else "not started (already recording this profile)")


def cmd_status(a, s):
    from .capture.status import status_text
    print(status_text(s))


def cmd_process(a, s):
    from .capture.process import MediaProcessor
    res = MediaProcessor(s).process(Path(a.media), Path(a.out))
    print(f"transcript: {res['transcript']}; frames ok: {res['frames_ok']}; freed {res['deleted_bytes']} bytes")


def cmd_clean(a, s):
    from .capture.retention import execute_clean, human_bytes, plan_clean
    folders = [Path(f) for f in a.folders]
    total = 0
    for folder in folders:
        plan = plan_clean(s, folder, keep_media=a.keep_media)
        if not plan.ok:
            print(f"{folder}: {plan.reason}")
            continue
        print(f"{folder}: {len(plan.to_delete)} items, {human_bytes(plan.bytes)} to free; "
              f"key frames kept: {len(plan.key_frames)}")
        if a.dry_run:
            continue
        if not a.yes and input("Delete? [y/N] ").strip().lower() not in ("y", "yes", "s", "si"):
            print("  skipped")
            continue
        total += execute_clean(s, plan)
    print(f"freed {human_bytes(total)}")


def cmd_install_autostart(a, s):
    from .capture.autostart import install_autostart
    for step in install_autostart(s.root, dry_run=a.dry_run):
        print(("would run: " if a.dry_run else "done: ") + step)


def cmd_uninstall_autostart(a, s):
    from .capture.autostart import uninstall_autostart
    for step in uninstall_autostart(dry_run=a.dry_run):
        print(("would run: " if a.dry_run else "done: ") + step)


# ---------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="fuffaguru", description="Goodbye FuffaGuru - reality-check your trading guru")
    ap.add_argument("--root", default=".", help="project folder with config/ and data/ (default: current folder)")
    ap.add_argument("--version", action="version", version=f"goodbye-fuffaguru {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("transcribe", help="speech to text with timestamps (faster-whisper)")
    p.add_argument("media"); p.add_argument("--model", default="small"); p.add_argument("--language")
    p.add_argument("--out"); p.set_defaults(func=cmd_transcribe)

    p = sub.add_parser("frames", help="one frame every N seconds (ffmpeg)")
    p.add_argument("video"); p.add_argument("--every", type=float, default=2.0); p.add_argument("--width", type=int)
    p.add_argument("--out-dir", default="frames"); p.set_defaults(func=cmd_frames)

    p = sub.add_parser("sheet", help="contact sheets: grids of small frames (ffmpeg)")
    p.add_argument("video"); p.add_argument("--every", type=float, default=10.0)
    p.add_argument("--cols", type=int, default=4); p.add_argument("--rows", type=int, default=4)
    p.add_argument("--out", default="sheet_%03d.jpg"); p.set_defaults(func=cmd_sheet)

    p = sub.add_parser("verify", help="replay a trades CSV on your OHLC bars and write the Reality Check")
    p.add_argument("trades"); p.add_argument("bars")
    p.add_argument("--cost", type=float, default=0.0, help="round-trip cost in price units")
    p.add_argument("--max-minutes", type=float, default=24 * 60)
    p.add_argument("--target-r", type=float, help="target in R when a trade has no target price")
    p.add_argument("--entry-bar", default="stop_only", choices=["stop_only", "skip", "full"])
    p.add_argument("--breakeven-at-r", type=float)
    p.add_argument("--tolerance", type=float, default=0.0, help="price tolerance for 'entry was traded'")
    p.add_argument("--out", default="verified_trades.csv"); p.add_argument("--report", default="REALITY_CHECK.md")
    p.add_argument("--title", default="Reality Check")
    p.add_argument("--claimed-win-rate", type=float); p.add_argument("--claimed-basis", default="unknown")
    p.add_argument("--claimed-trades-per-week", type=float)
    p.add_argument("--trials", type=int, default=1, help="number of variants/tests tried in total")
    p.add_argument("--sims", type=int, default=10_000); p.add_argument("--min-trades", type=int, default=30)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("freeze", help="freeze a recipe (JSON/YAML) with sha256 before testing")
    p.add_argument("recipe"); p.add_argument("--out"); p.set_defaults(func=cmd_freeze)
    p = sub.add_parser("check-freeze", help="check that a frozen recipe was not edited")
    p.add_argument("frozen"); p.set_defaults(func=cmd_check_freeze)

    p = sub.add_parser("setup", help="check tools, choose the browser for cookies, create folders")
    p.add_argument("--browser"); p.add_argument("--non-interactive", action="store_true")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("follow", help="follow a profile (URL, or @handle with --platform)")
    p.add_argument("target"); p.add_argument("--platform", choices=["youtube", "tiktok", "instagram"])
    p.add_argument("--history", action="store_true", help="also download the public history now")
    p.add_argument("--limit", type=int); p.set_defaults(func=cmd_follow)
    p = sub.add_parser("unfollow"); p.add_argument("key"); p.set_defaults(func=cmd_unfollow)
    p = sub.add_parser("profiles", help="list followed profiles"); p.set_defaults(func=cmd_profiles)

    p = sub.add_parser("history", help="download, transcribe and frame the public history of a profile")
    p.add_argument("key"); p.add_argument("--limit", type=int); p.add_argument("--since", help="YYYYMMDD")
    p.add_argument("--keep-media", action="store_true"); p.add_argument("--urls", help="text file with item URLs")
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("check-live", help="one live check of a profile (debug)")
    p.add_argument("key"); p.set_defaults(func=cmd_check_live)
    p = sub.add_parser("watch", help="watch all profiles for lives (every 60 s) and record them")
    p.add_argument("--interval", type=float); p.add_argument("--background", action="store_true")
    p.set_defaults(func=cmd_watch)
    p = sub.add_parser("record", help="record one live session now (used by the watcher)")
    p.add_argument("key"); p.set_defaults(func=cmd_record)
    p = sub.add_parser("status", help="profiles, recordings, last lives, alerts, disk")
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("process", help="transcribe + frames for one media file, then apply retention")
    p.add_argument("media"); p.add_argument("--out", required=True); p.set_defaults(func=cmd_process)
    p = sub.add_parser("clean", help="delete media and frames of analysed folders (asks first)")
    p.add_argument("folders", nargs="+"); p.add_argument("--yes", action="store_true")
    p.add_argument("--keep-media", action="store_true"); p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_clean)
    p = sub.add_parser("install-autostart", help="restart the watcher by itself after a reboot")
    p.add_argument("--dry-run", action="store_true"); p.set_defaults(func=cmd_install_autostart)
    p = sub.add_parser("uninstall-autostart"); p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_uninstall_autostart)
    return ap


def main(argv=None) -> int:
    from .capture.settings import Settings
    args = build_parser().parse_args(argv)
    settings = Settings.load(args.root)
    rc = args.func(args, settings)
    return int(rc or 0)


if __name__ == "__main__":
    sys.exit(main())
