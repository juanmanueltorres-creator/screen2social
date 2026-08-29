from __future__ import annotations

import asyncio
import math
import os

import simpleobsws
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from screen2social.errors import (
    ObsAlreadyRecordingError,
    ObsAuthError,
    ObsConfigError,
    ObsConnectionError,
    ObsNotRecordingError,
    ObsRequestError,
)


@dataclass(frozen=True)
class ObsConfig:
    host: str
    port: int
    password: str = field(repr=False)
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class ObsSceneNames:
    studio: str
    capture: str


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


def load_obs_scene_names(
    environ: Mapping[str, str] | None = None,
) -> ObsSceneNames:
    values = os.environ if environ is None else environ
    studio = values.get("SCREEN2SOCIAL_OBS_SCENE_STUDIO", "").strip()
    capture = values.get("SCREEN2SOCIAL_OBS_SCENE_CAPTURE", "").strip()

    if not studio:
        raise ObsConfigError("SCREEN2SOCIAL_OBS_SCENE_STUDIO is required")
    if not capture:
        raise ObsConfigError("SCREEN2SOCIAL_OBS_SCENE_CAPTURE is required")

    return ObsSceneNames(studio=studio, capture=capture)


def _make_client(config: ObsConfig) -> simpleobsws.WebSocketClient:
    return simpleobsws.WebSocketClient(
        url=f"ws://{config.host}:{config.port}",
        password=config.password,
    )


async def _call_obs_request_async(
    config: ObsConfig,
    request_type: str,
    request_data: dict | None = None,
):
    client = _make_client(config)
    try:
        try:
            await client.connect()
        except Exception as exc:
            raise ObsConnectionError("Could not connect to OBS WebSocket") from exc

        try:
            identified = await client.wait_until_identified(
                timeout=config.timeout_seconds
            )
        except Exception as exc:
            raise ObsConnectionError("OBS WebSocket identification failed") from exc

        if not identified:
            close_code = getattr(getattr(client, "ws", None), "close_code", None)
            if close_code == 4009:
                raise ObsAuthError("OBS WebSocket authentication failed")
            raise ObsConnectionError("OBS WebSocket identification timed out")

        try:
            return await client.call(
                simpleobsws.Request(request_type, request_data),
                timeout=config.timeout_seconds,
            )
        except Exception as exc:
            raise ObsRequestError(f"OBS request failed: {request_type}") from exc
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


def _call_obs_request(
    config: ObsConfig,
    request_type: str,
    request_data: dict | None = None,
):
    return asyncio.run(_call_obs_request_async(config, request_type, request_data))


def _active_config(config: ObsConfig | None) -> ObsConfig:
    return config if config is not None else load_obs_config()


def _require_ok(response, request_type: str) -> None:
    if response.ok():
        return

    code = getattr(response.requestStatus, "code", None)
    if request_type == "StartRecord" and code == 500:
        raise ObsAlreadyRecordingError("OBS is already recording")
    if request_type == "StopRecord" and code == 501:
        raise ObsNotRecordingError("OBS is not recording")
    raise ObsRequestError(f"OBS request failed: {request_type}")


def _require_bool(data: dict, key: str) -> bool:
    value = data.get(key)
    if type(value) is not bool:
        raise ObsRequestError(f"OBS response field is invalid: {key}")
    return value


def _require_non_negative_int(data: dict, key: str) -> int:
    value = data.get(key)
    if type(value) is not int or value < 0:
        raise ObsRequestError(f"OBS response field is invalid: {key}")
    return value


def _normalize_record_status(response) -> ObsRecordStatus:
    _require_ok(response, "GetRecordStatus")
    data = response.responseData
    if not isinstance(data, dict):
        raise ObsRequestError("OBS returned invalid GetRecordStatus data")

    timecode = data.get("outputTimecode")
    if not isinstance(timecode, str):
        raise ObsRequestError("OBS response field is invalid: outputTimecode")

    return ObsRecordStatus(
        active=_require_bool(data, "outputActive"),
        paused=_require_bool(data, "outputPaused"),
        timecode=timecode,
        duration_ms=_require_non_negative_int(data, "outputDuration"),
        bytes_written=_require_non_negative_int(data, "outputBytes"),
    )


def get_record_status(config: ObsConfig | None = None) -> ObsRecordStatus:
    response = _call_obs_request(_active_config(config), "GetRecordStatus")
    return _normalize_record_status(response)


def get_current_program_scene(config: ObsConfig | None = None) -> str:
    response = _call_obs_request(_active_config(config), "GetCurrentProgramScene")
    _require_ok(response, "GetCurrentProgramScene")

    data = response.responseData
    if not isinstance(data, dict):
        raise ObsRequestError("OBS returned invalid GetCurrentProgramScene data")

    scene_name = data.get("currentProgramSceneName")
    if not isinstance(scene_name, str) or not scene_name.strip():
        raise ObsRequestError(
            "OBS response field is invalid: currentProgramSceneName"
        )
    return scene_name


def set_current_program_scene(
    scene_name: str,
    config: ObsConfig | None = None,
) -> None:
    response = _call_obs_request(
        _active_config(config),
        "SetCurrentProgramScene",
        {"sceneName": scene_name},
    )
    _require_ok(response, "SetCurrentProgramScene")


def toggle_program_scene(
    scene_names: ObsSceneNames,
    config: ObsConfig | None = None,
) -> str:
    current = get_current_program_scene(config)
    target = scene_names.capture if current == scene_names.studio else scene_names.studio
    set_current_program_scene(target, config)
    return target


def start_recording(config: ObsConfig | None = None) -> None:
    response = _call_obs_request(_active_config(config), "StartRecord")
    _require_ok(response, "StartRecord")


def stop_recording(config: ObsConfig | None = None) -> ObsStopResult:
    response = _call_obs_request(_active_config(config), "StopRecord")
    _require_ok(response, "StopRecord")

    data = response.responseData
    if not isinstance(data, dict):
        raise ObsRequestError("OBS returned invalid StopRecord data")

    output_path = data.get("outputPath")
    if not isinstance(output_path, str) or not output_path.strip():
        raise ObsRequestError("OBS returned an invalid recording path")

    return ObsStopResult(output_path=Path(output_path))
