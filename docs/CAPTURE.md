# Capture: follow a trader on YouTube, TikTok and Instagram

> **Use it lawfully.** These tools act as *you*, with *your* account, for *your personal analysis*.
> You are responsible for respecting each platform's terms of service and the law of your country
> (copyright, privacy, recording laws). **Never republish** what you capture: share numbers and
> conclusions, not videos, frames or transcripts. If in doubt, don't capture.

## How your account is used (no secrets in the repository)

- `python -m fuffaguru setup` asks which browser you are logged in with. yt-dlp then reads that
  browser's cookies (`--cookies-from-browser`) at run time; nothing is copied into the project.
- Alternative: export a `cookies.txt` (Netscape format) with a browser extension into `secrets/`.
  `secrets/`, `config/settings.json` and `data/` are ignored by git.
- On Windows, recent Chrome and Edge versions block cookie reading by other programs while the
  browser is open. Firefox works; otherwise use the `cookies.txt` file.

## History: videos, shorts, reels, clips, past lives

```
python -m fuffaguru follow https://www.youtube.com/@SomeChannel
python -m fuffaguru history youtube:SomeChannel --limit 30
```

For each item: list -> download at 720p at most (with its info JSON) -> transcript with timestamps
-> a frame every 2 s + contact sheets -> **the video is deleted** (default; `--keep-media` keeps it).
Items already processed are skipped, so you can run it again to fetch only what is new.

| Platform | What works | Limits |
|---|---|---|
| YouTube | `/videos`, `/shorts`, `/streams` tabs via yt-dlp | Members-only or age-restricted content needs your cookies. |
| TikTok | Profile listing and videos via yt-dlp, with your cookies | TikTok changes often; update yt-dlp first (`pip install -U yt-dlp`). Past lives usually are not kept on the profile. |
| Instagram | Single posts and reels via yt-dlp, with your cookies | yt-dlp's profile listing has been unreliable for years: put the URLs in a text file and use `--urls FILE`. |

## Live streams: the watcher

```
python -m fuffaguru watch              # foreground
python -m fuffaguru watch --background # detached
python -m fuffaguru install-autostart  # restart it by itself after a reboot
python -m fuffaguru status
```

- Every **60 seconds** (not 5 minutes: you lose the beginning) each followed profile is checked.
- When a profile is live, a recorder starts for it: **3-minute pieces** copied with ffmpeg, each
  piece transcribed while the live goes on, then deleted once transcribed and its frames extracted.
- **One live = one folder.** Signed stream addresses expire and ffmpeg stops: the recorder reads a
  fresh address and continues in the *same* session. It closes the session only after **3
  consecutive "not live" checks** about a minute apart; then it writes `END` and closes the transcript.
- **"Already recording" is per profile**, and it covers the pause between two ffmpeg runs (a lock
  with a heartbeat), so several lives can be recorded at the same time and none twice.
- **No silent failures.** If the page says live but no valid stream is found for 3 checks in a row,
  you get an **alert**: always in `data/logs/alerts.log`, optionally as a desktop notification and on
  Telegram (set `notify.telegram` to true and put your bot token and chat id in the environment
  variables named in the settings; never in a file of the repository).
- **Disk space:** below `retention.min_free_gb` (20 GB by default) nothing is recorded or
  downloaded, and you get an alert. The check runs at every round, also after a reboot.

### Platform details

**TikTok** - what we learned the hard way:
- yt-dlp sometimes says "not live" while the profile is live: we read `https://www.tiktok.com/@name/live`
  ourselves, with your cookies, and fall back to yt-dlp only to find the stream.
- The bare `pull-*.flv` address answers 403: only the **signed** one (with its query string) works.
  In the page it is escaped: `&` must become `&`.
- Hosts change (`pull-flv-...`, `pull-f5-...`) and so do paths (`/game/`, `/stage/`): any `pull-*`
  host except `pull-hls`, any folder.
- `only_audio` variants are dropped; ffprobe must see **both video and audio** before recording.
- If the page gives no address, the room information endpoint used by many open-source recorders is
  tried. All of this can change without notice.

**YouTube** - yt-dlp gives the live HLS manifest; ffmpeg records it in pieces. Set
`watch.youtube_live_from_start` to true to record the whole live from its beginning with
`yt-dlp --live-from-start --wait-for-video` instead (one file, transcribed at the end).

**Instagram - EXPERIMENTAL, untested against a real live.** We first try yt-dlp on the live page;
then the DASH manifest (`.mpd`) exposed by Instagram's web API to logged-in users, read with your
cookies. Other open-source tools record Instagram lives from the same kind of manifest. Expect 403
errors, missing audio, and breakage whenever Instagram changes its private API. If it fails, you get
the alert described above: watch the live in your browser and take notes.

## After the analysis: cleaning

```
python -m fuffaguru clean data/tiktok/someone/live/20250106_150000          # shows what it frees, asks
python -m fuffaguru clean data/tiktok/someone/live/20250106_150000 --yes
python -m fuffaguru clean ... --keep-media                                   # deletes nothing
```

What stays: `transcript.md`, `trades.csv`, `report.md` and `key_frames.jpg` (4-6 key frames, chosen
in `key_frames.txt` by the analysis, else evenly spaced). Frames, contact sheets and media go.
**Nothing is deleted unless `report.md` and `trades.csv` exist and can be read back.** Every deletion
is logged in `data/logs/deletions.jsonl`.

## Folder layout

```
data/
  profiles.json, status.json
  logs/      watcher.log, alerts.log, deletions.jsonl, record_*.log
  <platform>/<handle>/
    history/<item>/   transcript/, frames/, sheets/, video.info.json
    live/<YYYYmmdd_HHMMSS>/
       session.json, events.log, END, transcript.md, transcript/, frames/, sheets/, parts/
       trades.csv, report.md, key_frames.txt, key_frames.jpg     (written by the analysis)
```
