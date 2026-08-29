from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from screen2social.errors import (
    TranscriptionNoAudioError,
    WhisperCliNotFoundError,
    WhisperModelNotFoundError,
)


@dataclass(frozen=True)
class TranscriptionToolchain:
    whisper_cli: Path
    model_path: Path


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
