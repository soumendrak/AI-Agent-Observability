from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LABS = [
    "00-setup",
    "01-first-trace",
    "02-read-a-trace",
    "03-incident",
    "04-fix-and-rerun",
    "05-evals",
    "06-alerts",
]
SPOILERS = ("swap", "BLR to HYD", "BLR>HYD", "TM-205", "B1EDC2", "does not match request:")


def text(name: str) -> str:
    return (ROOT / "labs" / f"{name}.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", LABS)
def test_lab_has_the_shared_structure(name: str) -> None:
    lab = text(name)
    for heading in ("## Goal", "## When", "## Steps", "## Checkpoint", "## If you're stuck"):
        assert f"\n{heading}" in lab, f"{name} lacks {heading}"


@pytest.mark.parametrize("name", [*LABS, "worksheet", "README"])
def test_no_answers_in_attendee_files(name: str) -> None:
    lab = text(name)
    for spoiler in SPOILERS:
        assert spoiler not in lab, f"{name} gives away {spoiler!r}"


def test_index_lists_every_lab_in_order() -> None:
    index = text("README")
    positions = [index.index(f"({name}.md)") for name in [*LABS, "worksheet"]]
    assert positions == sorted(positions)


def test_worksheet_has_the_evidence_table() -> None:
    sheet = text("worksheet")
    assert "| Span | Field | What it says | What the user asked |" in sheet
    assert sheet.count("\n| Q") >= 5
