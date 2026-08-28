import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from screen2social import __version__
from screen2social.errors import ProcessingError, Screen2SocialError
from screen2social.media import (
    Toolchain,
    discover_toolchain,
    extract_thumbnail,
    probe_media,
    transcode_linkedin,
)
from screen2social.metadata import build_metadata, write_metadata
from screen2social.paths import create_package_dir


@dataclass(frozen=True)
class ProcessResult:
    package_dir: Path
    video_path: Path
    thumbnail_path: Path
    metadata_path: Path


def process_recording(
    source: Path,
    *,
    ready_root: Path = Path("ready"),
    toolchain: Toolchain | None = None,
) -> ProcessResult:
    source = source.expanduser().resolve()
    active_toolchain = toolchain or discover_toolchain()
    source_info = probe_media(source, active_toolchain)

    try:
        package_dir = create_package_dir(source, ready_root)
    except Screen2SocialError:
        raise
    except OSError as exc:
        raise ProcessingError(f"Could not create output package: {exc}") from exc

    video_path = package_dir / "linkedin.mp4"
    thumbnail_path = package_dir / "thumbnail.png"
    metadata_path = package_dir / "metadata.json"

    try:
        transcode_linkedin(source, video_path, active_toolchain)
        output_info = probe_media(video_path, active_toolchain)
        extract_thumbnail(
            video_path,
            thumbnail_path,
            output_info.duration_seconds,
            active_toolchain,
        )
        metadata = build_metadata(
            source,
            source_info,
            output_info,
            processed_at=datetime.now(timezone.utc),
            pipeline_version=__version__,
            warnings=[],
        )
        write_metadata(metadata_path, metadata)
    except Screen2SocialError:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise
    except OSError as exc:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise ProcessingError(f"Could not build output package: {exc}") from exc

    return ProcessResult(
        package_dir=package_dir,
        video_path=video_path,
        thumbnail_path=thumbnail_path,
        metadata_path=metadata_path,
    )
