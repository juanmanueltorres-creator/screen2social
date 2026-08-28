import json
from unittest.mock import Mock

import pytest

from screen2social.errors import DependencyNotFoundError, InputNotFoundError
from screen2social.media import Toolchain, discover_toolchain, probe_media


def test_discover_toolchain_fails_when_ffmpeg_missing(monkeypatch):
    monkeypatch.setattr("screen2social.media.shutil.which", lambda name: None)

    with pytest.raises(DependencyNotFoundError) as exc:
        discover_toolchain()

    assert exc.value.code == "FFMPEG_NOT_FOUND"


def test_probe_media_fails_for_missing_input(tmp_path):
    toolchain = Toolchain(ffmpeg="ffmpeg", ffprobe="ffprobe")

    with pytest.raises(InputNotFoundError) as exc:
        probe_media(tmp_path / "missing.mkv", toolchain)

    assert exc.value.code == "INPUT_NOT_FOUND"


def test_probe_media_parses_video_and_optional_audio(tmp_path, monkeypatch):
    source = tmp_path / "demo.mkv"
    source.touch()
    payload = {
        "format": {"duration": "12.5"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }
    completed = Mock(returncode=0, stdout=json.dumps(payload), stderr="")
    monkeypatch.setattr("screen2social.media.subprocess.run", lambda *args, **kwargs: completed)

    info = probe_media(source, Toolchain(ffmpeg="ffmpeg", ffprobe="ffprobe"))

    assert info.duration_seconds == 12.5
    assert (info.width, info.height) == (1280, 720)
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"


def test_linkedin_command_is_structured_and_never_overwrites(tmp_path):
    from screen2social.media import build_linkedin_command

    source = tmp_path / "source.mkv"
    output = tmp_path / "linkedin.mp4"
    toolchain = Toolchain(ffmpeg="ffmpeg", ffprobe="ffprobe")

    command = build_linkedin_command(source, output, toolchain)

    assert isinstance(command, list)
    assert command[0] == "ffmpeg"
    assert "-n" in command
    assert "libx264" in command
    assert "yuv420p" in command
    assert "+faststart" in command
    assert str(source) in command
    assert str(output) in command


def test_transcode_linkedin_generates_expected_video(synthetic_video, tmp_path):
    from screen2social.media import transcode_linkedin

    toolchain = discover_toolchain()
    output = tmp_path / "linkedin.mp4"

    transcode_linkedin(synthetic_video, output, toolchain)
    info = probe_media(output, toolchain)

    assert output.is_file()
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"
    assert (info.width, info.height) == (1920, 1080)


def test_thumbnail_timestamp_uses_middle_for_short_video():
    from screen2social.media import choose_thumbnail_timestamp

    assert choose_thumbnail_timestamp(2.0) == 1.0


def test_thumbnail_timestamp_caps_at_five_seconds():
    from screen2social.media import choose_thumbnail_timestamp

    assert choose_thumbnail_timestamp(30.0) == 5.0


def test_extract_thumbnail_creates_png(synthetic_video, tmp_path):
    from screen2social.media import extract_thumbnail

    toolchain = discover_toolchain()
    output = tmp_path / "thumbnail.png"

    extract_thumbnail(synthetic_video, output, 2.0, toolchain)

    assert output.is_file()
    assert output.stat().st_size > 0
