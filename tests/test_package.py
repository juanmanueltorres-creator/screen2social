import json

import pytest

from screen2social.errors import (
    ProcessingError,
    TranscriptionFailedError,
    TranscriptionNoAudioError,
)
from screen2social.media import discover_toolchain
from screen2social.package import process_recording
from screen2social.transcription import TranscriptionResult, TranscriptionToolchain


def test_process_recording_creates_complete_social_package(synthetic_video, tmp_path):
    ready = tmp_path / "ready"

    result = process_recording(
        synthetic_video,
        ready_root=ready,
        toolchain=discover_toolchain(),
    )

    assert result.package_dir == ready / "source"
    assert result.video_path.name == "linkedin.mp4"
    assert result.thumbnail_path.name == "thumbnail.png"
    assert result.metadata_path.name == "metadata.json"
    assert result.post_path.name == "post.md"
    assert result.transcript_path is None
    assert result.subtitle_path is None
    assert result.video_path.is_file()
    assert result.thumbnail_path.is_file()
    assert result.metadata_path.is_file()
    assert result.post_path.is_file()

    post = result.post_path.read_text(encoding="utf-8")
    assert post.startswith("# source\n")
    assert "- Video: linkedin.mp4" in post
    assert "- Thumbnail: thumbnail.png" in post

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["output_dimensions"] == {"width": 1920, "height": 1080}
    assert metadata["steps"] == [
        "linkedin_transcode",
        "thumbnail",
        "post_template",
    ]
    assert "transcription" not in metadata
    assert metadata["pipeline_version"] == "0.3.0"


def test_process_recording_does_not_discover_whisper_without_flag(
    synthetic_video, tmp_path, monkeypatch
):
    def fail_if_called():
        raise AssertionError("Whisper discovery must not run without --transcribe")

    monkeypatch.setattr(
        "screen2social.package.discover_transcription_toolchain",
        fail_if_called,
    )

    result = process_recording(
        synthetic_video,
        ready_root=tmp_path / "ready",
        toolchain=discover_toolchain(),
    )

    assert result.transcript_path is None
    assert result.subtitle_path is None


def test_process_recording_rejects_no_audio_before_whisper_or_package_creation(
    synthetic_video_no_audio, tmp_path, monkeypatch
):
    ready = tmp_path / "ready"
    monkeypatch.delenv("SCREEN2SOCIAL_WHISPER_CLI", raising=False)
    monkeypatch.delenv("SCREEN2SOCIAL_WHISPER_MODEL", raising=False)

    with pytest.raises(TranscriptionNoAudioError) as exc:
        process_recording(
            synthetic_video_no_audio,
            ready_root=ready,
            toolchain=discover_toolchain(),
            transcribe=True,
        )

    assert exc.value.code == "TRANSCRIPTION_NO_AUDIO"
    assert synthetic_video_no_audio.is_file()
    assert not (ready / "silent-source").exists()


def test_process_recording_with_transcription_returns_six_artifacts(
    synthetic_video, tmp_path, monkeypatch
):
    ready = tmp_path / "ready"
    fake_toolchain = TranscriptionToolchain(
        whisper_cli=tmp_path / "whisper-cli.exe",
        model_path=tmp_path / "ggml-base.bin",
    )

    monkeypatch.setattr(
        "screen2social.package.discover_transcription_toolchain",
        lambda: fake_toolchain,
    )

    def fake_transcribe(source, package_dir, media_toolchain, transcription_toolchain):
        text = package_dir / "transcript.txt"
        srt = package_dir / "transcript.srt"
        text.write_text("hola\n", encoding="utf-8")
        srt.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nhola\n",
            encoding="utf-8",
        )
        return TranscriptionResult(text_path=text, subtitle_path=srt)

    monkeypatch.setattr(
        "screen2social.package.transcribe_recording",
        fake_transcribe,
    )

    result = process_recording(
        synthetic_video,
        ready_root=ready,
        toolchain=discover_toolchain(),
        transcribe=True,
    )

    assert result.transcript_path == ready / "source" / "transcript.txt"
    assert result.subtitle_path == ready / "source" / "transcript.srt"
    assert {path.name for path in result.package_dir.iterdir()} == {
        "linkedin.mp4",
        "thumbnail.png",
        "metadata.json",
        "post.md",
        "transcript.txt",
        "transcript.srt",
    }

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["steps"] == [
        "linkedin_transcode",
        "thumbnail",
        "post_template",
        "transcription",
    ]
    assert metadata["transcription"] == {
        "engine": "whisper.cpp",
        "language": "auto",
        "text_file": "transcript.txt",
        "subtitle_file": "transcript.srt",
    }


def test_process_recording_cleans_whole_package_when_transcription_fails(
    synthetic_video, tmp_path, monkeypatch
):
    ready = tmp_path / "ready"
    fake_toolchain = TranscriptionToolchain(
        whisper_cli=tmp_path / "whisper-cli.exe",
        model_path=tmp_path / "ggml-base.bin",
    )

    monkeypatch.setattr(
        "screen2social.package.discover_transcription_toolchain",
        lambda: fake_toolchain,
    )
    monkeypatch.setattr(
        "screen2social.package.transcribe_recording",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            TranscriptionFailedError("synthetic transcription failure")
        ),
    )

    with pytest.raises(TranscriptionFailedError):
        process_recording(
            synthetic_video,
            ready_root=ready,
            toolchain=discover_toolchain(),
            transcribe=True,
        )

    assert synthetic_video.is_file()
    assert not (ready / "source").exists()


def test_process_recording_removes_only_new_partial_package_on_domain_failure(
    synthetic_video, tmp_path, monkeypatch
):
    ready = tmp_path / "ready"

    def fail_transcode(*args, **kwargs):
        raise ProcessingError("synthetic failure")

    monkeypatch.setattr("screen2social.package.transcode_linkedin", fail_transcode)

    with pytest.raises(ProcessingError):
        process_recording(
            synthetic_video,
            ready_root=ready,
            toolchain=discover_toolchain(),
        )

    assert synthetic_video.is_file()
    assert not (ready / "source").exists()


def test_process_recording_maps_unexpected_io_error_and_cleans_package(
    synthetic_video, tmp_path, monkeypatch
):
    ready = tmp_path / "ready"

    def fail_metadata(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("screen2social.package.write_metadata", fail_metadata)

    with pytest.raises(ProcessingError) as exc:
        process_recording(
            synthetic_video,
            ready_root=ready,
            toolchain=discover_toolchain(),
        )

    assert exc.value.code == "PROCESSING_FAILED"
    assert synthetic_video.is_file()
    assert not (ready / "source").exists()


def test_process_recording_cleans_package_when_post_write_fails(
    synthetic_video, tmp_path, monkeypatch
):
    ready = tmp_path / "ready"

    def fail_post(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("screen2social.package.write_post", fail_post)

    with pytest.raises(ProcessingError) as exc:
        process_recording(
            synthetic_video,
            ready_root=ready,
            toolchain=discover_toolchain(),
        )

    assert exc.value.code == "PROCESSING_FAILED"
    assert synthetic_video.is_file()
    assert not (ready / "source").exists()
