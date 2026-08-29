from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from screen2social.errors import (
    TranscriptionFailedError,
    TranscriptionNoAudioError,
    WhisperCliNotFoundError,
    WhisperModelNotFoundError,
)
from screen2social.media import Toolchain


@dataclass(frozen=True)
class TranscriptionToolchain:
    whisper_cli: Path
    model_path: Path


@dataclass(frozen=True)
class TranscriptionResult:
    text_path: Path
    subtitle_path: Path


def discover_transcription_toolchain(
    environ: Mapping[str, str] | None = None,
) -> TranscriptionToolchain:
    active_environ = os.environ if environ is None else environ

    cli_value = active_environ.get("SCREEN2SOCIAL_WHISPER_CLI", "").strip()
    if not cli_value:
        raise WhisperCliNotFoundError(
            "SCREEN2SOCIAL_WHISPER_CLI is required when --transcribe is used"
        )
    whisper_cli = Path(cli_value).expanduser()
    if not whisper_cli.is_file():
        raise WhisperCliNotFoundError(
            f"whisper-cli does not exist: {whisper_cli}"
        )

    model_value = active_environ.get("SCREEN2SOCIAL_WHISPER_MODEL", "").strip()
    if not model_value:
        raise WhisperModelNotFoundError(
            "SCREEN2SOCIAL_WHISPER_MODEL is required when --transcribe is used"
        )
    model_path = Path(model_value).expanduser()
    if not model_path.is_file():
        raise WhisperModelNotFoundError(
            f"Whisper model does not exist: {model_path}"
        )

    return TranscriptionToolchain(
        whisper_cli=whisper_cli.resolve(),
        model_path=model_path.resolve(),
    )


def ensure_audio_available(audio_codec: str | None) -> None:
    if audio_codec is None:
        raise TranscriptionNoAudioError(
            "Input recording has no audio stream to transcribe"
        )


def build_audio_extract_command(
    source: Path,
    output: Path,
    toolchain: Toolchain,
) -> list[str]:
    return [
        toolchain.ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
        "-i",
        str(source),
        "-map",
        "0:a:0",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output),
    ]


def extract_transcription_audio(
    source: Path,
    output: Path,
    toolchain: Toolchain,
) -> None:
    try:
        completed = subprocess.run(
            build_audio_extract_command(source, output, toolchain),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise TranscriptionFailedError(
            f"Could not launch ffmpeg for transcription audio: {exc}"
        ) from exc

    if completed.returncode != 0:
        raise TranscriptionFailedError(
            completed.stderr.strip()
            or "ffmpeg failed while creating transcription audio"
        )


def build_whisper_command(
    audio: Path,
    output_base: Path,
    toolchain: TranscriptionToolchain,
) -> list[str]:
    return [
        str(toolchain.whisper_cli),
        "--model",
        str(toolchain.model_path),
        "--file",
        str(audio),
        "--language",
        "auto",
        "--output-txt",
        "--output-srt",
        "--output-file",
        str(output_base),
    ]


def run_whisper(
    audio: Path,
    output_base: Path,
    toolchain: TranscriptionToolchain,
) -> TranscriptionResult:
    try:
        completed = subprocess.run(
            build_whisper_command(audio, output_base, toolchain),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise TranscriptionFailedError(
            f"Could not launch whisper-cli: {exc}"
        ) from exc

    if completed.returncode != 0:
        raise TranscriptionFailedError(
            completed.stderr.strip() or "whisper-cli failed during transcription"
        )

    text_path = output_base.with_suffix(".txt")
    subtitle_path = output_base.with_suffix(".srt")
    if not text_path.is_file():
        raise TranscriptionFailedError(
            f"whisper-cli did not create expected output: {text_path.name}"
        )
    if not subtitle_path.is_file():
        raise TranscriptionFailedError(
            f"whisper-cli did not create expected output: {subtitle_path.name}"
        )

    return TranscriptionResult(
        text_path=text_path,
        subtitle_path=subtitle_path,
    )


def transcribe_recording(
    source: Path,
    package_dir: Path,
    media_toolchain: Toolchain,
    transcription_toolchain: TranscriptionToolchain,
) -> TranscriptionResult:
    temporary_audio = package_dir / ".transcription.wav"
    output_base = package_dir / "transcript"

    try:
        extract_transcription_audio(source, temporary_audio, media_toolchain)
        result = run_whisper(
            temporary_audio,
            output_base,
            transcription_toolchain,
        )
    except TranscriptionFailedError:
        try:
            temporary_audio.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    try:
        temporary_audio.unlink(missing_ok=True)
    except OSError as exc:
        raise TranscriptionFailedError(
            f"Could not remove temporary transcription audio: {exc}"
        ) from exc

    return result
