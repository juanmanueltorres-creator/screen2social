from screen2social import __version__
from screen2social.cli import build_parser


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
