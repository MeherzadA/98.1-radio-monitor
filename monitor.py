"""
98.1 Radio Monitor

Listens to a live radio stream, transcribes it in short clips using
OpenAI's Whisper speech-to-text model, and sends a Telegram message
whenever one of the KEYWORDS below is mentioned on air.

How it works, step by step:
  1. Use ffmpeg to record a short clip (CHUNK_SECONDS) of the live stream.
  2. Run that clip through Whisper to get a text transcript.
  3. Check the transcript for any of the KEYWORDS (not case-sensitive).
  4. If a keyword shows up, send an alert message to Telegram.
  5. Delete the clip and go back to step 1.

This is a single loop - record, transcribe, check, repeat - so there's
no multithreading or queues to keep track of. The tradeoff is that
while a clip is being transcribed, the stream isn't being recorded, so
there's a small gap (usually a couple of seconds) between clips. For
catching keyword mentions on the radio, that's fine.
"""

import os
from datetime import datetime
import subprocess

import requests
import whisper
from dotenv import load_dotenv

# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------
# Secrets and machine-specific paths live in a .env file (see .env.example)
# so they don't end up committed to the repo.
load_dotenv()

STREAM_URL = os.environ["STREAM_URL"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# If ffmpeg isn't on your PATH, set FFMPEG_PATH in .env to its full path.
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

# How long each recorded clip is, in seconds.
CHUNK_SECONDS = 20

# Words/phrases to listen for. Matching is case-insensitive and just
# checks whether the word appears anywhere in the transcript.
KEYWORDS = ["key", "word"]

# Whisper model size. "tiny" is fast enough to run in real time on a
# normal CPU. Bigger models ("base", "small", "medium", "large") are
# more accurate at picking out words, but take longer to transcribe
# each clip - if a clip takes longer than CHUNK_SECONDS to transcribe,
# the monitor will start falling behind the live stream.
WHISPER_MODEL = "tiny"

# The recorded clip is saved to this file, transcribed, then deleted.
# Using one fixed filename (overwritten each time) keeps the folder clean.
CHUNK_FILENAME = "current_chunk.wav"


def send_telegram_message(text):
    """Send a text message to the Telegram chat configured above."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}

    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.ok:
            print("Telegram message sent.")
        else:
            print(f"Telegram API error: {response.text}")
    except requests.RequestException as error:
        print(f"Could not reach Telegram: {error}")


def record_clip():
    """Record CHUNK_SECONDS of the live stream to CHUNK_FILENAME."""
    command = [
        FFMPEG_PATH,
        "-y",                    # overwrite CHUNK_FILENAME if it already exists
        "-i", STREAM_URL,
        "-t", str(CHUNK_SECONDS),
        "-ac", "1",              # mono audio
        "-ar", "16000",          # 16kHz sample rate, what Whisper expects
        "-acodec", "pcm_s16le",
        CHUNK_FILENAME,
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def transcribe_clip(model):
    """Run the recorded clip through Whisper and return the transcript text."""
    result = model.transcribe(CHUNK_FILENAME)
    return result["text"]


def contains_keyword(text):
    """Return True if any KEYWORDS entry appears in text (case-insensitive)."""
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS)


def main():
    print(f"Loading Whisper model ({WHISPER_MODEL})...")
    model = whisper.load_model(WHISPER_MODEL)
    print("Model loaded. Starting monitor - press Ctrl+C to stop.")

    send_telegram_message("98.1 radio monitor started.")

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Recording {CHUNK_SECONDS}s clip...")
        record_clip()

        try:
            print("Transcribing...")
            transcript = transcribe_clip(model)
        except Exception as error:
            print(f"Transcription failed, skipping this clip: {error}")
            continue
        finally:
            if os.path.exists(CHUNK_FILENAME):
                os.remove(CHUNK_FILENAME)

        print(f"Heard: {transcript.strip()!r}")

        if contains_keyword(transcript):
            send_telegram_message(
                f"Keyword detected!\n\n{transcript.strip()}\n\n{timestamp}"
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
