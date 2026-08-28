from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from screen2social.errors import (
    DependencyNotFoundError,
    InputNotFoundError,
    ProbeError,
    ProcessingError,
)


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


LINKEDIN_VIDEO_FILTER = (
    "scale=1920:1080:force_original_aspect_ratio=decrease,"
    "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1"
)


def build_linkedin_command(source: Path, output: Path, toolchain: Toolchain) -> list[str]:
    return [
        toolchain.ffmpeg,
        "-hide_banner", "-loglevel", "error", "-n",
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-vf", LINKEDIN_VIDEO_FILTER,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(output),
    ]


def transcode_linkedin(source: Path, output: Path, toolchain: Toolchain) -> None:
    command = build_linkedin_command(source, output, toolchain)
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise ProcessingError(
            completed.stderr.strip() or "ffmpeg failed while creating linkedin.mp4"
        )
