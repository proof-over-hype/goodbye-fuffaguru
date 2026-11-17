import json
import types

import pytest

from fuffaguru.capture import detect
from fuffaguru.capture.detect import (InstagramDetector, TikTokDetector, extract_tiktok_stream_urls,
                                      find_urls_with_extension, has_video_and_audio, parse_ffprobe_streams,
                                      unescape_url)
from fuffaguru.capture.profiles import Profile, parse_profile
from fuffaguru.capture.settings import Settings

# A fake TikTok live page: escaped addresses as they appear inside the page's JSON.
PAGE = r'''<script id="SIGI_STATE">{"LiveRoom":{"liveRoomUserInfo":{"liveRoom":{"status":2,
"streamData":"{\"data\":{\"origin\":{\"main\":{\"flv\":\"https:\\/\\/pull-flv-l11.example-cdn.com\\/stage\\/stream-123_or4.flv?expire=1\\u0026sign=abc\"}},
\"hd\":{\"main\":{\"flv\":\"https:\\/\\/pull-f5-tt03.example-cdn.com\\/game\\/stream-123_hd.flv?expire=1\\u0026sign=def\"}},
\"ao\":{\"main\":{\"flv\":\"https:\\/\\/pull-flv-l11.example-cdn.com\\/stage\\/stream-123_only_audio.flv?expire=1\\u0026sign=x\"}},
\"hls\":{\"main\":{\"hls\":\"https:\\/\\/pull-hls-l11.example-cdn.com\\/stage\\/stream-123.flv?expire=1\\u0026sign=y\"}},
\"bare\":\"https:\\/\\/pull-flv-q1.example-cdn.com\\/stage\\/stream-999.flv\"}}"}},"roomId":"7300000000000000001"}}</script>'''


def test_unescape_url_handles_any_depth():
    assert unescape_url(r"https:\\/\\/a.com\\/x.flv?a=1\\u0026b=2") == "https://a.com/x.flv?a=1&b=2"
    assert unescape_url(r"https:\/\/a.com\/x.flv?a=1&b=2") == "https://a.com/x.flv?a=1&b=2"


def test_tiktok_urls_signed_any_pull_host_and_path_no_hls_no_audio_only():
    urls = extract_tiktok_stream_urls(PAGE)
    assert urls == [
        "https://pull-flv-l11.example-cdn.com/stage/stream-123_or4.flv?expire=1&sign=abc",
        "https://pull-f5-tt03.example-cdn.com/game/stream-123_hd.flv?expire=1&sign=def",
    ]
    assert all("&" in u and "\\" not in u for u in urls)


def test_tiktok_markers():
    assert detect.tiktok_page_says_live(PAGE)
    assert detect.tiktok_room_id(PAGE) == "7300000000000000001"
    assert not detect.tiktok_page_says_live('{"liveRoom":{"status":4}}')


def settings(tmp_path):
    return Settings(tmp_path)


def test_tiktok_detector_live_with_stream(tmp_path):
    d = TikTokDetector(settings(tmp_path), fetch=lambda url, jar, headers=None: PAGE)
    d._jar_loaded = True
    st = d.check(Profile("tiktok", "someone"))
    assert st.live and st.stream_url.endswith("sign=abc")


def test_tiktok_detector_live_without_stream(tmp_path):
    page = '{"liveRoom":{"status":2}} no addresses here'
    d = TikTokDetector(settings(tmp_path), fetch=lambda url, jar, headers=None: page, run_json=lambda cmd: None)
    d._jar_loaded = True
    st = d.check(Profile("tiktok", "someone"))
    assert st.live and st.stream_url is None


def test_tiktok_detector_not_live_and_unreadable(tmp_path):
    d = TikTokDetector(settings(tmp_path), fetch=lambda url, jar, headers=None: "<html>offline</html>")
    d._jar_loaded = True
    assert not d.check(Profile("tiktok", "x")).live

    def boom(url, jar, headers=None):
        raise OSError("403")
    d2 = TikTokDetector(settings(tmp_path), fetch=boom)
    d2._jar_loaded = True
    assert not d2.check(Profile("tiktok", "x")).live


def test_instagram_mpd_from_api(tmp_path):
    answers = {
        "web_profile_info": json.dumps({"data": {"user": {"id": "42"}}}),
        "web_info": json.dumps({"dash_abr_playback_url": "https://scontent.example.com/live/abc.mpd?tok=1"}),
    }

    def fetch(url, jar, headers=None):
        return answers["web_profile_info"] if "web_profile_info" in url else answers["web_info"]
    d = InstagramDetector(settings(tmp_path), fetch=fetch, run_json=lambda cmd: None)
    d._jar_loaded = True
    st = d.check(Profile("instagram", "someone"))
    assert st.live and st.stream_url.endswith(".mpd?tok=1")
    assert find_urls_with_extension(r'"u":"https:\/\/x.com\/a.mpd?t=1"', ".mpd") == ["https://x.com/a.mpd?t=1"]


def test_ffprobe_needs_video_and_audio():
    both = json.dumps({"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]})
    only = json.dumps({"streams": [{"codec_type": "audio"}]})
    assert parse_ffprobe_streams(both) == {"video", "audio"}
    fake = lambda out: (lambda cmd, **kw: types.SimpleNamespace(stdout=out, returncode=0))
    assert has_video_and_audio("u", runner=fake(both))
    assert not has_video_and_audio("u", runner=fake(only))
    assert not has_video_and_audio("u", runner=fake("not json"))


@pytest.mark.parametrize("text,platform,key", [
    ("https://www.tiktok.com/@some.one/live", None, "tiktok:some.one"),
    ("https://www.youtube.com/@SomeChannel/streams", None, "youtube:SomeChannel"),
    ("https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv", None, "youtube:UCabcdefghijklmnopqrstuv"),
    ("https://www.instagram.com/some_one/", None, "instagram:some_one"),
    ("@someone", "tiktok", "tiktok:someone"),
])
def test_parse_profile(text, platform, key):
    p = parse_profile(text, platform)
    assert p.key == key


def test_profile_urls():
    p = Profile("tiktok", "abc")
    assert p.live_url == "https://www.tiktok.com/@abc/live"
    assert Profile("youtube", "abc").history_urls()[-1].endswith("/streams")
    with pytest.raises(ValueError):
        parse_profile("@x")
