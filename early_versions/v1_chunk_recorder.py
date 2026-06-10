"""
Second iteration.

Records fixed-length clips back-to-back and transcribes each one for
keyword mentions, sending a Telegram alert when one is found. Recording
and transcribing happen in separate threads (connected by a queue) so
the next clip can start recording while the previous one is being
transcribed.

Kept here as a reference for how the project evolved. The current
version (../monitor.py) does the same job with a single plain loop -
much easier to follow, at the cost of a small recording gap while each
clip is transcribed.
"""

import os
from datetime import datetime
from queue import Queue
import subprocess
import threading
import time

import requests
import whisper
from dotenv import load_dotenv

load_dotenv()

STREAM_URL = os.environ["STREAM_URL"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

CHUNK_DURATION = 20
KEYWORDS = ["key", "word"]

audio_queue = Queue()
model = whisper.load_model("base")


def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}

    try:
        response = requests.post(url, data=data)
        if response.ok:
            print("telegram msg success")
    except Exception:
        print("Failed to send telegram msg")


def record_chunk():
    filename = f"chunk_{int(time.time())}.wav"

    command = [
        FFMPEG_PATH,
        "-y",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", STREAM_URL,
        "-t", str(CHUNK_DURATION),
        "-ac", "1",
        "-ar", "16000",
        "-acodec", "pcm_s16le",
        filename,
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return filename


def transcribe_chunk(filename):
    result = model.transcribe(filename)
    return result["text"]


def check_for_keyword(transcribed_text, keywords):
    text_lower = transcribed_text.lower()

    for keyword in keywords:
        if keyword.lower() in text_lower:
            return transcribed_text

    return None


def recorder():
    chunk_number = 1

    while True:
        formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"--- Recording chunk {chunk_number} | {formatted_datetime} ---")

        filename = record_chunk()
        audio_queue.put(filename)
        chunk_number += 1


def transcriber():
    while True:
        file_to_transcribe = audio_queue.get()

        print(f"Now transcribing {file_to_transcribe}")
        transcribed_text = transcribe_chunk(file_to_transcribe)
        print(f"Transcription: {transcribed_text}")

        possible_alert = check_for_keyword(transcribed_text, KEYWORDS)
        if possible_alert:
            send_telegram_msg(
                f"Possible keyword mentioned:\n{possible_alert}\n--------------\n"
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        audio_queue.task_done()
        os.remove(file_to_transcribe)


def main():
    send_telegram_msg("98.1 Tracking started.")

    t1 = threading.Thread(target=recorder)
    t2 = threading.Thread(target=transcriber)

    t1.start()
    t2.start()

    t1.join()
    t2.join()


if __name__ == "__main__":
    main()
