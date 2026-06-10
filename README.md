# 98.1 Radio Monitor

A small script that listens to a live radio stream, transcribes it
using OpenAI's [Whisper](https://github.com/openai/whisper) speech-to-
text model, and sends a Telegram message whenever a chosen keyword is
mentioned on air.

## How it works

`monitor.py` runs a simple loop:

1. Record a short clip (20 seconds by default) of the live stream with `ffmpeg`.
2. Transcribe the clip with Whisper.
3. Check the transcript for any of the configured keywords.
4. If a keyword is found, send an alert to a Telegram chat.
5. Delete the clip and repeat.

## Setup

### 1. Install ffmpeg

Download a build from [ffmpeg.org](https://ffmpeg.org/download.html)
and either add it to your PATH, or note the full path to `ffmpeg.exe`
for the `.env` file below.

### 2. Install Python dependencies

```
pip install -r requirements.txt
```

### 3. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram and create a new bot to get a bot token.
2. Message your new bot, then visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` to find your chat ID.

### 4. Configure the project

Copy `.env.example` to `.env` and fill in your values:

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
STREAM_URL=...
FFMPEG_PATH=ffmpeg
```

### 5. Run it

```
python monitor.py
```

You'll get a "monitor started" message on Telegram, then an alert
message any time one of the keywords in `monitor.py` (`KEYWORDS`) is
heard in the stream.

## Notes

- The Whisper model defaults to `tiny`, which is fast enough to run in
  real time on a CPU. Larger models (`base`, `small`, etc.) are more
  accurate but need more time per clip - if a clip takes longer than
  `CHUNK_SECONDS` to transcribe, the monitor falls behind the live stream.
- Some radio stations issue stream URLs tied to a session that expires
  after a while. If the monitor stops being able to connect, grab a
  fresh stream URL and update `STREAM_URL` in `.env`.

## `early_versions/`

Earlier prototypes, kept for reference:

- `v0_stream_segmenter.py` - the very first test, just splits the live
  stream into sequential audio files with ffmpeg.
- `v1_chunk_recorder.py` - adds transcription and Telegram alerts, with
  recording and transcription running on separate threads.

`monitor.py` is the current version and does the same job as
`v1_chunk_recorder.py` with a single straightforward loop instead.
