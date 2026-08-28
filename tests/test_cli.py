from screen2social import __version__
from screen2social.cli import build_parser


def test_parser_uses_screen2social_program_name():
    parser = build_parser()
    assert parser.prog == "screen2social"


def test_version_is_exposed():
    assert __version__ == "0.1.0"
