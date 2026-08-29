from pathlib import Path

import pytest

from screen2social.errors import (
    TranscriptionNoAudioError,
    WhisperCliNotFoundError,
    WhisperModelNotFoundError,
)
from screen2social.transcription import (
    TranscriptionToolchain,
    discover_transcription_toolchain,
    ensure_audio_available,
)


def test_discover_transcription_toolchain_requires_cli_configuration(tmp_path):
    model = tmp_path / "ggml-base.bin"
    model.touch()

    with pytest.raises(WhisperCliNotFoundError) as exc:
        discover_transcription_toolchain(
            {"SCREEN2SOCIAL_WHISPER_MODEL": str(model)}
        )

    assert exc.value.code == "WHISPER_CLI_NOT_FOUND"


def test_discover_transcription_toolchain_rejects_invalid_cli_path(tmp_path):
    model = tmp_path / "ggml-base.bin"
    model.touch()

    with pytest.raises(WhisperCliNotFoundError):
        discover_transcription_toolchain(
            {
                "SCREEN2SOCIAL_WHISPER_CLI": str(tmp_path / "missing-whisper-cli.exe"),
                "SCREEN2SOCIAL_WHISPER_MODEL": str(model),
            }
        )


def test_discover_transcription_toolchain_requires_model_configuration(tmp_path):
    cli = tmp_path / "whisper-cli.exe"
    cli.touch()

    with pytest.raises(WhisperModelNotFoundError) as exc:
        discover_transcription_toolchain(
            {"SCREEN2SOCIAL_WHISPER_CLI": str(cli)}
        )

    assert exc.value.code == "WHISPER_MODEL_NOT_FOUND"


def test_discover_transcription_toolchain_rejects_invalid_model_path(tmp_path):
    cli = tmp_path / "whisper-cli.exe"
    cli.touch()

    with pytest.raises(WhisperModelNotFoundError):
        discover_transcription_toolchain(
            {
                "SCREEN2SOCIAL_WHISPER_CLI": str(cli),
                "SCREEN2SOCIAL_WHISPER_MODEL": str(tmp_path / "missing-model.bin"),
            }
        )


def test_discover_transcription_toolchain_returns_resolved_paths(tmp_path):
    cli = tmp_path / "whisper-cli.exe"
    model = tmp_path / "ggml-base.bin"
    cli.touch()
    model.touch()

    result = discover_transcription_toolchain(
        {
            "SCREEN2SOCIAL_WHISPER_CLI": str(cli),
            "SCREEN2SOCIAL_WHISPER_MODEL": str(model),
        }
    )

    assert result == TranscriptionToolchain(
        whisper_cli=cli.resolve(),
        model_path=model.resolve(),
    )


def test_ensure_audio_available_accepts_audio_codec():
    ensure_audio_available("aac")


def test_ensure_audio_available_rejects_missing_audio():
    with pytest.raises(TranscriptionNoAudioError) as exc:
        ensure_audio_available(None)

    assert exc.value.code == "TRANSCRIPTION_NO_AUDIO"
