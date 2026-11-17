import json

from fuffaguru.capture.autostart import cron_line, install_autostart, windows_commands
from fuffaguru.capture.retention import disk_ok, execute_clean, plan_clean
from fuffaguru.capture.settings import Settings
from fuffaguru.capture.status import status_text


def analysed_folder(tmp_path, report=True, trades=True):
    folder = tmp_path / "data" / "tiktok" / "x" / "live" / "20250106_100000"
    (folder / "frames" / "part1").mkdir(parents=True)
    (folder / "sheets").mkdir()
    for i in range(10):
        (folder / "frames" / "part1" / f"frame_{i:06d}.jpg").write_bytes(b"\xff" * 100)
    (folder / "sheets" / "sheet_001.jpg").write_bytes(b"\xff" * 100)
    (folder / "parts").mkdir()
    (folder / "parts" / "part_20250106-100000_r01.ts").write_bytes(b"\0" * 5000)
    (folder / "transcript.md").write_text("[10:00:00] hello", encoding="utf-8")
    if report:
        (folder / "report.md").write_text("# Analysis\nverdict", encoding="utf-8")
    if trades:
        (folder / "trades.csv").write_text("trade_id,status\nt1,taken\n", encoding="utf-8")
    return folder


def test_without_report_nothing_is_deleted(tmp_path):
    s = Settings(tmp_path)
    folder = analysed_folder(tmp_path, report=False)
    before = sorted(p.relative_to(folder) for p in folder.rglob("*"))
    plan = plan_clean(s, folder)
    assert not plan.ok and "report.md" in plan.reason
    assert execute_clean(s, plan) == 0
    assert sorted(p.relative_to(folder) for p in folder.rglob("*")) == before


def test_without_trades_csv_nothing_is_deleted(tmp_path):
    s = Settings(tmp_path)
    folder = analysed_folder(tmp_path, trades=False)
    assert not plan_clean(s, folder).ok
    assert (folder / "frames").exists() and (folder / "parts" / "part_20250106-100000_r01.ts").exists()


def test_clean_keeps_evidence_and_logs_deletions(tmp_path):
    s = Settings(tmp_path)
    folder = analysed_folder(tmp_path)
    plan = plan_clean(s, folder)
    assert plan.ok and plan.bytes > 5000
    freed = execute_clean(s, plan)
    assert freed == plan.bytes
    assert not (folder / "frames").exists() and not (folder / "sheets").exists()
    assert not list(folder.rglob("*.ts"))
    for kept in ("transcript.md", "report.md", "trades.csv"):
        assert (folder / kept).exists()
    assert (folder / "key_frames.jpg").exists() or (folder / "key_frames").exists()
    log = [json.loads(x) for x in (s.logs_dir / "deletions.jsonl").read_text().splitlines()]
    assert len(log) == len(plan.to_delete)


def test_keep_media_disables_cleaning(tmp_path):
    s = Settings(tmp_path)
    folder = analysed_folder(tmp_path)
    plan = plan_clean(s, folder, keep_media=True)
    assert not plan.ok and execute_clean(s, plan) == 0
    assert (folder / "frames").exists()


def test_disk_threshold_alerts_and_blocks(tmp_path):
    s = Settings(tmp_path)

    class N:
        sent = []

        def alert(self, t, m):
            self.sent.append(t)
    n = N()
    assert not disk_ok(s, n, free=lambda p: 5.0)
    assert n.sent == ["Low disk space"]
    assert disk_ok(s, n, free=lambda p: 500.0)


def test_autostart_dry_run(tmp_path):
    steps = install_autostart(tmp_path, python="python", dry_run=True, system="Windows")
    assert "schtasks" in steps[0] and "ONLOGON" in steps[0] and "watch" in steps[0]
    assert install_autostart(tmp_path, python="python", dry_run=True, system="Darwin")[1].startswith("launchctl")
    assert "@reboot" in cron_line(tmp_path, "python")
    assert windows_commands(tmp_path, "python")[0][0] == "schtasks"


def test_status_text_runs_without_data(tmp_path):
    out = status_text(Settings(tmp_path))
    assert "No profiles followed yet" in out
