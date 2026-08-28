import json
from datetime import datetime, timezone

from screen2social.media import MediaInfo
from screen2social.metadata import build_metadata, write_metadata


def test_metadata_contains_source_output_steps_and_version(tmp_path):
    source = tmp_path / "demo.mkv"
    source.touch()
    source_info = MediaInfo(12.0, 1280, 720, "h264", "aac")
    output_info = MediaInfo(12.0, 1920, 1080, "h264", "aac")
    now = datetime(2026, 8, 28, 20, 30, tzinfo=timezone.utc)

    payload = build_metadata(
        source,
        source_info,
        output_info,
        processed_at=now,
        pipeline_version="0.1.0",
        warnings=[],
    )

    assert payload["source_file"] == str(source.resolve())
    assert payload["source_duration_seconds"] == 12.0
    assert payload["output_duration_seconds"] == 12.0
    assert payload["output_dimensions"] == {"width": 1920, "height": 1080}
    assert payload["steps"] == ["linkedin_transcode", "thumbnail"]
    assert payload["pipeline_version"] == "0.1.0"
    assert payload["warnings"] == []

    destination = tmp_path / "metadata.json"
    write_metadata(destination, payload)
    assert json.loads(destination.read_text(encoding="utf-8")) == payload
