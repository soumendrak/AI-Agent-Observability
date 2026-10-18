import re
import shlex
from pathlib import Path

import pytest

from tripmate import cli

ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted([ROOT / "README.md", *ROOT.glob("docs/*.md"), *ROOT.glob("labs/*.md")])
COMMAND = re.compile(r"uv run ws ([^`\n]*)")
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def commands(doc: Path) -> list[str]:
    return [m.group(1).strip() for m in COMMAND.finditer(doc.read_text(encoding="utf-8"))]


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.relative_to(ROOT).as_posix())
def test_every_documented_ws_command_parses(doc: Path) -> None:
    for command in commands(doc):
        cli.parser().parse_args(shlex.split(command))


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.relative_to(ROOT).as_posix())
def test_relative_links_point_at_files(doc: Path) -> None:
    for target in LINK.findall(doc.read_text(encoding="utf-8")):
        if not target.startswith(("http://", "https://", "mailto:")):
            assert (doc.parent / target).exists(), f"{doc.name} links to missing {target}"


def test_readme_covers_the_five_minute_setup() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert {"doctor", 'run "Book HYD to BLR on 2026-10-31"', "case 0 --exporter console"} <= set(
        commands(ROOT / "README.md")
    )
    for needed in ("uv sync", "Copy-Item .env.example .env", "cp .env.example .env", "pair"):
        assert needed in readme
