import argparse
from collections.abc import Sequence
from pathlib import Path

from screen2social import __version__
from screen2social.errors import Screen2SocialError
from screen2social.package import process_recording


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="screen2social",
        description="Turn local screen recordings into social-ready media packages.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    process_parser = subparsers.add_parser(
        "process", help="Process an existing local recording"
    )
    process_parser.add_argument("input")
    process_parser.add_argument("--ready-dir", default="ready")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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
