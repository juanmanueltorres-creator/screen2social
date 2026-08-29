import json
from datetime import datetime
from pathlib import Path

from screen2social.media import MediaInfo


def build_metadata(
    source: Path,
    source_info: MediaInfo,
    output_info: MediaInfo,
    *,
    processed_at: datetime,
    pipeline_version: str,
    warnings: list[str],
    transcription_performed: bool = False,
) -> dict[str, object]:
    steps = ["linkedin_transcode", "thumbnail", "post_template"]
    if transcription_performed:
        steps.append("transcription")

    payload: dict[str, object] = {
        "source_file": str(source.expanduser().resolve()),
        "processed_at": processed_at.isoformat(),
        "source_duration_seconds": source_info.duration_seconds,
        "output_duration_seconds": output_info.duration_seconds,
        "source_dimensions": {"width": source_info.width, "height": source_info.height},
        "output_dimensions": {"width": output_info.width, "height": output_info.height},
        "source_codecs": {"video": source_info.video_codec, "audio": source_info.audio_codec},
        "output_codecs": {"video": output_info.video_codec, "audio": output_info.audio_codec},
        "steps": steps,
        "warnings": list(warnings),
        "pipeline_version": pipeline_version,
    }

    if transcription_performed:
        payload["transcription"] = {
            "engine": "whisper.cpp",
            "language": "auto",
            "text_file": "transcript.txt",
            "subtitle_file": "transcript.srt",
        }

    return payload


def write_metadata(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
