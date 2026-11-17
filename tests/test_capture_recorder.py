"""The three lessons that cost us lives: (b) one session across expiring addresses,
(c) a lock per profile that also covers the pause between two ffmpeg runs,
(d) an alert when the page says live but no stream can be recorded."""

import json

from fuffaguru.capture.detect import LiveStatus
from fuffaguru.capture.locks import ProfileLock
from fuffaguru.capture.profiles import Profile, ProfileStore
from fuffaguru.capture.recorder import LiveRecorder, PartProcessor
from fuffaguru.capture.settings import Settings
from fuffaguru.capture.watcher import Watcher
from fuffaguru.transcribe import Segment


class ScriptedDetector:
    """Returns the scripted statuses in order, then 'not live' forever."""

    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    def check(self, profile):
        self.calls += 1
        return self.statuses.pop(0) if self.statuses else LiveStatus(False, None, "offline")


class FakeFFmpeg:
    """Writes one finished piece per run, as ffmpeg would before the signed address expires."""

    def __init__(self):
        self.urls = []

    def __call__(self, url, parts_dir, run_idx):
        self.urls.append(url)
        (parts_dir / f"part_20250106-1{run_idx:02d}000_r{run_idx:02d}.ts").write_bytes(b"\0" * 1000)
        return 1  # "403 / expired": ffmpeg exits with an error


class FakeProcessor:
    def __init__(self, settings):
        self.settings = settings
        self.seen = []

    def process(self, media, out_dir, name=None):
        from fuffaguru.capture.retention import delete_media_if_transcribed
        from fuffaguru.transcribe import save_transcript
        self.seen.append(media.name)
        md = save_transcript([Segment(0, 2, f"text of {media.stem}")], out_dir / "transcript" / f"{media.stem}.json")
        save_transcript([Segment(0, 2, f"text of {media.stem}")], out_dir / "transcript" / f"{media.stem}.md")
        delete_media_if_transcribed(self.settings, media, md)
        return {}


def make(tmp_path, statuses, **kw):
    s = Settings(tmp_path)
    clock = {"t": 1000.0}

    def sleep(sec):
        clock["t"] += sec

    def tick():
        clock["t"] += 1
        return clock["t"]
    rec = LiveRecorder(
        Profile("tiktok", "trader_a"), s, ScriptedDetector(statuses),
        runner=kw.pop("runner", FakeFFmpeg()), probe=kw.pop("probe", lambda url: True),
        processor=kw.pop("processor", FakeProcessor(s)), sleep=kw.pop("sleep", sleep), clock=tick,
        disk_check=lambda: True, live_processing=False, **kw)
    rec.notifier.sender = lambda title, msg: None  # no desktop popups in tests
    return s, rec


def live(url):
    return LiveStatus(True, url, "signed stream found")


OFF = LiveStatus(False, None, "offline")


def test_b_expired_address_continues_in_the_same_session(tmp_path):
    # three ffmpeg runs with three different signed addresses, two short "not live" blips in between
    statuses = [live("u1"), live("u2"), OFF, live("u3"), OFF, OFF, OFF]
    s, rec = make(tmp_path, statuses)
    session = rec.run()
    live_dir = tmp_path / "data" / "tiktok" / "trader_a" / "live"
    assert [p.name for p in live_dir.iterdir() if p.is_dir()] == [session.name]  # ONE folder
    assert rec.runner.urls == ["u1", "u2", "u3"]  # a fresh address after each exit
    state = json.loads((session / "session.json").read_text())
    assert state["state"] == "ended" and state["ffmpeg_runs"] == 3
    assert (session / "END").exists()
    text = (session / "transcript.md").read_text(encoding="utf-8")
    assert text.count("text of part_") == 3  # transcript closed with all pieces
    assert not list((session / "parts").glob("*.ts"))  # pieces deleted once transcribed
    assert not (live_dir / ".recording.lock").exists()  # lock released at the end


def test_b_session_needs_consecutive_negative_checks(tmp_path):
    statuses = [live("u1"), OFF, OFF, live("u2"), OFF, OFF, OFF]
    _, rec = make(tmp_path, statuses)
    rec.run()
    assert rec.runner.urls == ["u1", "u2"]  # two blips did not close the session


def test_c_lock_is_per_profile_and_covers_the_pause(tmp_path):
    observed = []
    s = Settings(tmp_path)
    other = Profile("youtube", "trader_b")

    def sleep_and_look(sec):
        # while the recorder waits between two ffmpeg runs, the watcher looks at the locks
        observed.append((ProfileLock(rec.live_dir, clock=rec.clock).busy(),
                         ProfileLock(other.folder(s.data_dir) / "live", clock=rec.clock).busy()))

    statuses = [live("u1"), LiveStatus(True, None, "page says live, no address"), live("u2"), OFF, OFF, OFF]
    _, rec = make(tmp_path, statuses, sleep=sleep_and_look)
    rec.run()
    assert observed and all(this for this, _ in observed)  # busy also while paused
    assert not any(that for _, that in observed)            # other profiles stay free


def test_c_watcher_skips_busy_profile_and_starts_the_free_one(tmp_path):
    s = Settings(tmp_path)
    store = ProfileStore(s.data_dir)
    a, b = Profile("tiktok", "trader_a"), Profile("tiktok", "trader_b")
    store.add(a)
    store.add(b)
    lock = ProfileLock(a.folder(s.data_dir) / "live")
    assert lock.acquire("s1")
    lock.heartbeat(state="waiting")  # recorder paused between two ffmpeg runs
    started = []

    class AlwaysLive:
        def __init__(self, *args):
            pass

        def check(self, profile):
            return live("u")
    w = Watcher(s, store=store, detector_factory=AlwaysLive, spawn=lambda p: started.append(p.key),
                disk_check=lambda: True)
    actions = w.check_once()
    assert actions == {"tiktok:trader_a": "busy", "tiktok:trader_b": "started"}
    assert started == ["tiktok:trader_b"]
    lock.release()


def test_c_stale_lock_is_not_busy(tmp_path):
    lock = ProfileLock(tmp_path, stale_seconds=10, clock=lambda: 0.0)
    assert lock.acquire()
    later = ProfileLock(tmp_path, stale_seconds=10, clock=lambda: 100.0)
    assert not later.busy()
    dead = ProfileLock(tmp_path, stale_seconds=10, clock=lambda: 1.0, is_alive=lambda pid: False)
    assert not dead.busy()


def test_d_alert_when_live_but_no_stream(tmp_path):
    no_stream = LiveStatus(True, None, "page says live, no usable stream address")
    statuses = [no_stream] * 4 + [OFF, OFF, OFF]
    s, rec = make(tmp_path, statuses)
    rec.notifier.sender = None
    sent = []
    rec.notifier.sender = lambda title, msg: sent.append(title)
    rec.run()
    assert len(sent) == 1 and "not being recorded" in sent[0]  # exactly one alert, not silence, not spam
    alerts = (s.logs_dir / "alerts.log").read_text(encoding="utf-8")
    assert "ALERT" in alerts and "tiktok:trader_a" in alerts


def test_d_stream_without_video_and_audio_also_alerts(tmp_path):
    statuses = [live("audio-only")] * 3 + [OFF, OFF, OFF]
    s, rec = make(tmp_path, statuses, probe=lambda url: False)
    sent = []
    rec.notifier.sender = lambda title, msg: sent.append(msg)
    rec.run()
    assert sent and rec.runner.urls == []  # never recorded an invalid stream


def test_d_no_alert_when_recording_works(tmp_path):
    s, rec = make(tmp_path, [live("u1"), OFF, OFF, OFF])
    sent = []
    rec.notifier.sender = lambda title, msg: sent.append(title)
    rec.run()
    assert sent == []


def test_part_processor_keeps_the_newest_piece_while_recording(tmp_path):
    s = Settings(tmp_path)
    session = tmp_path / "sess"
    (session / "parts").mkdir(parents=True)
    for i in range(3):
        (session / "parts" / f"part_20250106-10{i}000_r01.ts").write_bytes(b"x")
    proc = FakeProcessor(s)
    pp = PartProcessor(session, proc)
    assert pp.step(final=False) == 2
    assert pp.step(final=True) == 1
    assert "[10:20:00]" in (session / "transcript.md").read_text(encoding="utf-8")
