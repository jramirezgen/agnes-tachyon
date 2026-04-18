from tachyon import __version__
from tachyon.cli import build_parser


def test_version_is_semver_like():
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_cli_exposes_core_commands():
    parser = build_parser()
    help_text = parser.format_help()
    for command in ("version", "server", "health", "train", "stack", "portable"):
        assert command in help_text
