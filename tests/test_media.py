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
