from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from screen2social.errors import DependencyNotFoundError, InputNotFoundError, ProbeError


@dataclass(frozen=True)
class Toolchain:
    ffmpeg: str
    ffprobe: str


@dataclass(frozen=True)
class MediaInfo:
    duration_seconds: float
    width: int
    height: int
    video_codec: str
    audio_codec: str | None


def discover_toolchain() -> Toolchain:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise DependencyNotFoundError("FFMPEG_NOT_FOUND", "ffmpeg was not found on PATH")
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise DependencyNotFoundError("FFPROBE_NOT_FOUND", "ffprobe was not found on PATH")
    return Toolchain(ffmpeg=ffmpeg, ffprobe=ffprobe)


def probe_media(path: Path, toolchain: Toolchain) -> MediaInfo:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise InputNotFoundError(f"Input file does not exist: {path}")

    command = [
        toolchain.ffprobe,
        "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,codec_name,width,height",
        "-of", "json",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise ProbeError(completed.stderr.strip() or f"ffprobe failed for {path}")

    try:
        payload = json.loads(completed.stdout)
        video = next(stream for stream in payload["streams"] if stream.get("codec_type") == "video")
        audio = next((stream for stream in payload["streams"] if stream.get("codec_type") == "audio"), None)
        return MediaInfo(
            duration_seconds=float(payload["format"]["duration"]),
            width=int(video["width"]),
            height=int(video["height"]),
            video_codec=str(video["codec_name"]),
            audio_codec=str(audio["codec_name"]) if audio else None,
        )
    except (KeyError, StopIteration, TypeError, ValueError) as exc:
        raise ProbeError(f"Could not parse ffprobe output for {path}") from exc
