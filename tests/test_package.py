import json

import pytest

from screen2social.errors import ProcessingError
from screen2social.media import discover_toolchain
from screen2social.package import process_recording


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
    assert metadata["pipeline_version"] == "0.3.0"


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
