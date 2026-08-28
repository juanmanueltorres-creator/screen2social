from pathlib import Path

import pytest

from screen2social import __version__
from screen2social.cli import build_parser, main
from screen2social.errors import ObsConnectionError
from screen2social.obs import ObsRecordStatus, ObsStopResult


def test_parser_uses_screen2social_program_name():
    parser = build_parser()
    assert parser.prog == "screen2social"


def test_version_is_exposed():
    assert __version__ == "0.1.0"


def test_process_command_parses_input_and_ready_dir():
    parser = build_parser()
    args = parser.parse_args(["process", "demo.mkv", "--ready-dir", "out"])

    assert args.command == "process"
    assert args.input == "demo.mkv"
    assert args.ready_dir == "out"


def test_doctor_command_is_available():
    parser = build_parser()
    args = parser.parse_args(["doctor"])
    assert args.command == "doctor"


@pytest.mark.parametrize("command", ["status", "record", "stop"])
def test_obs_commands_are_available(command):
    parser = build_parser()
    args = parser.parse_args([command])
    assert args.command == command


def test_status_prints_stopped_state(monkeypatch, capsys):
    monkeypatch.setattr(
        "screen2social.cli.get_record_status",
        lambda: ObsRecordStatus(False, False, "00:00:00.000", 0, 0),
    )

    assert main(["status"]) == 0
    assert capsys.readouterr().out == "OBS: connected\nRecording: stopped\n"


def test_status_prints_active_timecode(monkeypatch, capsys):
    monkeypatch.setattr(
        "screen2social.cli.get_record_status",
        lambda: ObsRecordStatus(True, False, "00:00:03.500", 3500, 1000),
    )

    assert main(["status"]) == 0
    assert capsys.readouterr().out == (
        "OBS: connected\nRecording: active\nTimecode: 00:00:03.500\n"
    )


def test_status_prints_paused_state(monkeypatch, capsys):
    monkeypatch.setattr(
        "screen2social.cli.get_record_status",
        lambda: ObsRecordStatus(True, True, "00:00:05.000", 5000, 2000),
    )

    assert main(["status"]) == 0
    assert capsys.readouterr().out == (
        "OBS: connected\nRecording: paused\nTimecode: 00:00:05.000\n"
    )


def test_record_prints_started(monkeypatch, capsys):
    monkeypatch.setattr("screen2social.cli.start_recording", lambda: None)

    assert main(["record"]) == 0
    assert capsys.readouterr().out == "RECORDING: started\n"


def test_stop_prints_returned_path(monkeypatch, capsys):
    path = Path(r"C:\Users\Juan\Videos\demo.mkv")
    monkeypatch.setattr(
        "screen2social.cli.stop_recording",
        lambda: ObsStopResult(path),
    )

    assert main(["stop"]) == 0
    assert capsys.readouterr().out == f"RECORDING: stopped\nFILE: {path}\n"


def test_obs_error_uses_stable_code_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(
        "screen2social.cli.get_record_status",
        lambda: (_ for _ in ()).throw(
            ObsConnectionError("Could not connect to OBS WebSocket")
        ),
    )

    assert main(["status"]) == 1
    assert capsys.readouterr().out == (
        "OBS_CONNECTION_FAILED: Could not connect to OBS WebSocket\n"
    )
