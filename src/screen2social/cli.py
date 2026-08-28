import argparse
from collections.abc import Sequence
from pathlib import Path

from screen2social import __version__
from screen2social.errors import Screen2SocialError
from screen2social.media import discover_toolchain
from screen2social.obs import get_record_status, start_recording, stop_recording
from screen2social.package import process_recording


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="screen2social",
        description="Turn local screen recordings into social-ready media packages.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("doctor", help="Check local Screen2Social dependencies")
    subparsers.add_parser("status", help="Show OBS recording status")
    subparsers.add_parser("record", help="Start OBS recording")
    subparsers.add_parser("stop", help="Stop OBS recording and show the saved file")

    process_parser = subparsers.add_parser(
        "process", help="Process an existing local recording"
    )
    process_parser.add_argument("input")
    process_parser.add_argument("--ready-dir", default="ready")
    return parser


def _run_obs_command(action) -> int:
    try:
        return action()
    except Screen2SocialError as exc:
        print(f"{exc.code}: {exc}")
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        try:
            toolchain = discover_toolchain()
        except Screen2SocialError as exc:
            print(f"{exc.code}: {exc}")
            return 1
        print(f"OK ffmpeg: {toolchain.ffmpeg}")
        print(f"OK ffprobe: {toolchain.ffprobe}")
        return 0

    if args.command == "status":
        def show_status():
            status = get_record_status()
            print("OBS: connected")
            if not status.active:
                print("Recording: stopped")
                return 0
            print("Recording: paused" if status.paused else "Recording: active")
            print(f"Timecode: {status.timecode}")
            return 0

        return _run_obs_command(show_status)

    if args.command == "record":
        def start():
            start_recording()
            print("RECORDING: started")
            return 0

        return _run_obs_command(start)

    if args.command == "stop":
        def stop():
            result = stop_recording()
            print("RECORDING: stopped")
            print(f"FILE: {result.output_path}")
            return 0

        return _run_obs_command(stop)

    if args.command == "process":
        try:
            result = process_recording(
                Path(args.input),
                ready_root=Path(args.ready_dir),
            )
        except Screen2SocialError as exc:
            print(f"{exc.code}: {exc}")
            return 1
        print(f"READY: {result.package_dir}")
        return 0

    parser.print_help()
    return 0
