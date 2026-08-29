from pathlib import Path
from types import SimpleNamespace

import pytest

from screen2social.errors import (
    TranscriptionFailedError,
    TranscriptionNoAudioError,
    WhisperCliNotFoundError,
    WhisperModelNotFoundError,
)
from screen2social.media import Toolchain
from screen2social.transcription import (
    TranscriptionResult,
    TranscriptionToolchain,
    build_audio_extract_command,
    build_whisper_command,
    discover_transcription_toolchain,
    ensure_audio_available,
    extract_transcription_audio,
    run_whisper,
    transcribe_recording,
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


def test_build_audio_extract_command_is_mono_16khz_pcm(tmp_path):
    source = tmp_path / "source.mkv"
    output = tmp_path / ".transcription.wav"
    toolchain = Toolchain(ffmpeg="ffmpeg", ffprobe="ffprobe")

    assert build_audio_extract_command(source, output, toolchain) == [
        "ffmpeg",
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


def test_build_whisper_command_requests_auto_txt_and_srt(tmp_path):
    audio = tmp_path / ".transcription.wav"
    output_base = tmp_path / "transcript"
    toolchain = TranscriptionToolchain(
        whisper_cli=Path("whisper-cli.exe"),
        model_path=Path("ggml-base.bin"),
    )

    assert build_whisper_command(audio, output_base, toolchain) == [
        "whisper-cli.exe",
        "--model",
        "ggml-base.bin",
        "--file",
        str(audio),
        "--language",
        "auto",
        "--output-txt",
        "--output-srt",
        "--output-file",
        str(output_base),
    ]


def test_extract_transcription_audio_maps_ffmpeg_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "screen2social.transcription.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr="bad audio"),
    )

    with pytest.raises(TranscriptionFailedError) as exc:
        extract_transcription_audio(
            tmp_path / "source.mkv",
            tmp_path / ".transcription.wav",
            Toolchain(ffmpeg="ffmpeg", ffprobe="ffprobe"),
        )

    assert exc.value.code == "TRANSCRIPTION_FAILED"
    assert "bad audio" in str(exc.value)


def test_extract_transcription_audio_maps_launch_oserror(tmp_path, monkeypatch):
    def raise_oserror(*args, **kwargs):
        raise OSError("launch failed")

    monkeypatch.setattr("screen2social.transcription.subprocess.run", raise_oserror)

    with pytest.raises(TranscriptionFailedError) as exc:
        extract_transcription_audio(
            tmp_path / "source.mkv",
            tmp_path / ".transcription.wav",
            Toolchain(ffmpeg="ffmpeg", ffprobe="ffprobe"),
        )

    assert "launch failed" in str(exc.value)


def test_run_whisper_maps_nonzero_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "screen2social.transcription.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr="decode failed"),
    )
    toolchain = TranscriptionToolchain(
        whisper_cli=tmp_path / "whisper-cli.exe",
        model_path=tmp_path / "ggml-base.bin",
    )

    with pytest.raises(TranscriptionFailedError) as exc:
        run_whisper(tmp_path / ".transcription.wav", tmp_path / "transcript", toolchain)

    assert "decode failed" in str(exc.value)


def test_run_whisper_maps_launch_oserror(tmp_path, monkeypatch):
    def raise_oserror(*args, **kwargs):
        raise OSError("cannot execute")

    monkeypatch.setattr("screen2social.transcription.subprocess.run", raise_oserror)
    toolchain = TranscriptionToolchain(
        whisper_cli=tmp_path / "whisper-cli.exe",
        model_path=tmp_path / "ggml-base.bin",
    )

    with pytest.raises(TranscriptionFailedError) as exc:
        run_whisper(tmp_path / ".transcription.wav", tmp_path / "transcript", toolchain)

    assert "cannot execute" in str(exc.value)


def test_run_whisper_rejects_missing_srt(tmp_path, monkeypatch):
    output_base = tmp_path / "transcript"

    def fake_run(*args, **kwargs):
        output_base.with_suffix(".txt").write_text("hola\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("screen2social.transcription.subprocess.run", fake_run)
    toolchain = TranscriptionToolchain(
        tmp_path / "whisper-cli.exe",
        tmp_path / "ggml-base.bin",
    )

    with pytest.raises(TranscriptionFailedError):
        run_whisper(tmp_path / ".transcription.wav", output_base, toolchain)


def test_run_whisper_rejects_missing_txt(tmp_path, monkeypatch):
    output_base = tmp_path / "transcript"

    def fake_run(*args, **kwargs):
        output_base.with_suffix(".srt").write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nhola\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("screen2social.transcription.subprocess.run", fake_run)
    toolchain = TranscriptionToolchain(
        tmp_path / "whisper-cli.exe",
        tmp_path / "ggml-base.bin",
    )

    with pytest.raises(TranscriptionFailedError):
        run_whisper(tmp_path / ".transcription.wav", output_base, toolchain)


def test_run_whisper_returns_expected_paths(tmp_path, monkeypatch):
    output_base = tmp_path / "transcript"

    def fake_run(*args, **kwargs):
        output_base.with_suffix(".txt").write_text("hola\n", encoding="utf-8")
        output_base.with_suffix(".srt").write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nhola\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("screen2social.transcription.subprocess.run", fake_run)
    toolchain = TranscriptionToolchain(
        tmp_path / "whisper-cli.exe",
        tmp_path / "ggml-base.bin",
    )

    assert run_whisper(
        tmp_path / ".transcription.wav",
        output_base,
        toolchain,
    ) == TranscriptionResult(
        text_path=output_base.with_suffix(".txt"),
        subtitle_path=output_base.with_suffix(".srt"),
    )


def test_transcribe_recording_removes_temporary_wav_on_success(tmp_path, monkeypatch):
    package_dir = tmp_path / "ready" / "source"
    package_dir.mkdir(parents=True)

    def fake_extract(source, output, toolchain):
        output.write_bytes(b"wav")

    def fake_whisper(audio, output_base, toolchain):
        text = output_base.with_suffix(".txt")
        srt = output_base.with_suffix(".srt")
        text.write_text("hola\n", encoding="utf-8")
        srt.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nhola\n",
            encoding="utf-8",
        )
        return TranscriptionResult(text, srt)

    monkeypatch.setattr(
        "screen2social.transcription.extract_transcription_audio",
        fake_extract,
    )
    monkeypatch.setattr("screen2social.transcription.run_whisper", fake_whisper)

    result = transcribe_recording(
        tmp_path / "source.mkv",
        package_dir,
        Toolchain(ffmpeg="ffmpeg", ffprobe="ffprobe"),
        TranscriptionToolchain(
            tmp_path / "whisper-cli.exe",
            tmp_path / "ggml-base.bin",
        ),
    )

    assert result.text_path.is_file()
    assert result.subtitle_path.is_file()
    assert not (package_dir / ".transcription.wav").exists()


def test_transcribe_recording_removes_temporary_wav_on_failure(tmp_path, monkeypatch):
    package_dir = tmp_path / "ready" / "source"
    package_dir.mkdir(parents=True)

    def fake_extract(source, output, toolchain):
        output.write_bytes(b"wav")

    def fail_whisper(*args, **kwargs):
        raise TranscriptionFailedError("decode failed")

    monkeypatch.setattr(
        "screen2social.transcription.extract_transcription_audio",
        fake_extract,
    )
    monkeypatch.setattr("screen2social.transcription.run_whisper", fail_whisper)

    with pytest.raises(TranscriptionFailedError):
        transcribe_recording(
            tmp_path / "source.mkv",
            package_dir,
            Toolchain(ffmpeg="ffmpeg", ffprobe="ffprobe"),
            TranscriptionToolchain(
                tmp_path / "whisper-cli.exe",
                tmp_path / "ggml-base.bin",
            ),
        )

    assert not (package_dir / ".transcription.wav").exists()
