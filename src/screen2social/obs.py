from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from screen2social.errors import ObsConfigError


@dataclass(frozen=True)
class ObsConfig:
    host: str
    port: int
    password: str = field(repr=False)
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class ObsRecordStatus:
    active: bool
    paused: bool
    timecode: str
    duration_ms: int
    bytes_written: int


@dataclass(frozen=True)
class ObsStopResult:
    output_path: Path


def load_obs_config(environ: Mapping[str, str] | None = None) -> ObsConfig:
    values = os.environ if environ is None else environ

    host = values.get("SCREEN2SOCIAL_OBS_HOST", "localhost").strip()
    password = values.get("SCREEN2SOCIAL_OBS_PASSWORD", "").strip()
    port_raw = values.get("SCREEN2SOCIAL_OBS_PORT", "4455").strip()
    timeout_raw = values.get("SCREEN2SOCIAL_OBS_TIMEOUT_SECONDS", "5.0").strip()

    if not host:
        raise ObsConfigError("OBS host must not be empty")
    if not password:
        raise ObsConfigError("SCREEN2SOCIAL_OBS_PASSWORD is required")

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ObsConfigError("OBS port must be an integer from 1 to 65535") from exc
    if not 1 <= port <= 65535:
        raise ObsConfigError("OBS port must be an integer from 1 to 65535")

    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise ObsConfigError("OBS timeout must be a finite number greater than 0") from exc
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ObsConfigError("OBS timeout must be a finite number greater than 0")

    return ObsConfig(
        host=host,
        port=port,
        password=password,
        timeout_seconds=timeout_seconds,
    )
