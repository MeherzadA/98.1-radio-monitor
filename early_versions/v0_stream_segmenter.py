"""
Earliest experiment.

Just connects to the live stream with ffmpeg and splits it into a
series of fixed-length audio files (chunk_000.wav, chunk_001.wav, ...)
using ffmpeg's "segment" muxer. No Python logic at all - this was used
to confirm ffmpeg could connect to the stream and produce clean,
back-to-back chunks before any transcription or alerting was added.
"""

import os
import subprocess

from dotenv import load_dotenv

load_dotenv()

STREAM_URL = os.environ["STREAM_URL"]
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

CHUNK_SECONDS = 20

command = [
    FFMPEG_PATH,
    "-i", STREAM_URL,
    "-f", "segment",
    "-segment_time", str(CHUNK_SECONDS),
    "-acodec", "libmp3lame",
    "chunk_%03d.wav",
]

subprocess.run(command)
