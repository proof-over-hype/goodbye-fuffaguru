import sys
import types

import pytest

from fuffaguru import frames, transcribe


def test_timestamps_and_srt():
    assert transcribe.format_timestamp(3725.5) == "01:02:05"
    assert transcribe.format_timestamp(1.25, srt=True) == "00:00:01,250"
    segs = [transcribe.Segment(0.0, 1.5, "hello"), transcribe.Segment(2.0, 3.0, "world")]
    srt = transcribe.segments_to_srt(segs)
    assert "00:00:00,000 --> 00:00:01,500" in srt and "world" in srt
    assert transcribe.segments_to_markdown(segs).startswith("[00:00:00] hello")


def test_transcribe_with_a_fake_model(tmp_path):
    media = tmp_path / "a.wav"
    media.write_bytes(b"x")

    class FakeModel:
        def transcribe(self, path, language=None, vad_filter=True):
            seg = types.SimpleNamespace(start=0.0, end=2.0, text=" buy here ")
            return [seg], None

    out = transcribe.transcribe(media, model=FakeModel())
    assert out[0].text == "buy here"
    path = transcribe.save_transcript(out, tmp_path / "t.json")
    assert transcribe.load_segments(path)[0].end == 2.0


def test_missing_faster_whisper_gives_a_clear_message(monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(ImportError, match="pip install faster-whisper"):
        transcribe._load_model("small", "auto", "default")


def test_ffmpeg_commands():
    cmd = frames.build_frames_cmd("v.mp4", "out", every_seconds=2, width=640)
    assert "fps=1/2,scale=640:-2" in cmd and cmd[-1].endswith("frame_%06d.jpg")
    sheet = frames.build_contact_sheet_cmd("v.mp4", "s_%03d.jpg", every_seconds=10, cols=4, rows=3)
    assert any("tile=4x3" in c for c in sheet)
    assert frames.build_frame_at_cmd("v.mp4", 12.5, "f.jpg")[6] == "12.500"
    assert frames.frame_time(1, 2.0) == 1.0


def test_missing_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(frames.shutil, "which", lambda name: None)
    with pytest.raises(FileNotFoundError, match="ffmpeg"):
        frames.extract_frames(tmp_path / "v.mp4", tmp_path / "out")
