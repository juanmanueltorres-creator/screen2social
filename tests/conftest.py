import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def synthetic_video(tmp_path: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg is required for media integration tests")

    output = tmp_path / "source.mkv"
    command = [
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(output),
    ]
    subprocess.run(command, check=True)
    return output
