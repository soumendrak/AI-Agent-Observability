import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_FIX = ROOT / "tests" / "reference_guard.py"
SPOILERS = (
    "BLR to HYD",
    "BLR>HYD",
    "BLR → HYD",
    "BLR->HYD",
    "Bengaluru to Hyderabad",
    "Bangalore to Hyderabad",
    '"origin": "BLR", "destination": "HYD"',
    "origin requested=HYD booked=BLR",
    "caught mismatch on origin, destination",
    "does not match request: origin, destination",
    "swapped origin",
    "swap origin",
    "origin and destination swapped",
    "swapped the origin",
    "TM-205",
    "B1EDC2",
    "31/10/2026",
)
ANSWER_FILES = {
    "src/tripmate/data/flights.json": "the return flight the broken booking lands on",
    "tests/reference_guard.py": "the reference fix CI applies to prove Case 2 can pass",
    "tests/eval_cases.json": "evaluator parity cases, including Case 1 and Case 2",
    "tests/test_cases.py": "pins each case's planted fault",
    "tests/test_cli.py": "pins the CLI output of the fault and the fix",
    "tests/test_eval_parity.py": "pins the evaluator comment on Case 2",
    "tests/test_request_parser.py": "parses the Case 1 date",
    "tests/test_leaks.py": "this list of spoilers",
}
SKIPPED = {"uv.lock", "package-lock.json"}


def words(text: str) -> str:
    return " " + " ".join(re.findall(r"[a-z0-9]+", text.casefold())) + " "


def fix_lines() -> list[str]:
    lines = REFERENCE_FIX.read_text(encoding="utf-8").splitlines()[1:]
    return [line.strip() for line in lines if len(words(line).split()) >= 5]


def spoilers_in(text: str) -> list[str]:
    found = words(text)
    return [s for s in (*SPOILERS, *fix_lines()) if words(s) in found]


def shipped() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout.split("\0")
    return sorted(n for n in listed if n and n not in SKIPPED and (ROOT / n).is_file())


@pytest.mark.parametrize("name", [n for n in shipped() if n not in ANSWER_FILES])
def test_no_answers_in_anything_that_ships(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8", errors="replace")
    assert spoilers_in(text) == []


@pytest.mark.parametrize("name", sorted(ANSWER_FILES))
def test_every_allowlisted_file_still_needs_its_answers(name: str) -> None:
    assert spoilers_in((ROOT / name).read_text(encoding="utf-8")) != []


def test_the_copy_paste_guard_sees_through_formatting() -> None:
    planted = """
    It booked bLr  to\nHyD (blr>hyd, BLR -> HYD, BLR→HYD), flight tm-205, PNR b1edc2.
    bengaluru TO hyderabad, or Bangalore to Hyderabad. {"origin":"BLR","destination":"HYD"}
    booking_matches_request: FAIL: mismatch: origin requested=HYD booked=BLR
    guard: caught mismatch on origin, destination
    tool book_flight [ERROR] does not match request: origin, destination
    The model Swapped Origin and destination; it swapped the origin, so origin and destination
    swapped. Swap origin back. Case 1 used 31/10/2026.
    """
    planted += "\n".join(f"        {line}" for line in fix_lines())
    assert spoilers_in(planted) == [*SPOILERS, *fix_lines()]
    assert len(fix_lines()) == 2


@pytest.mark.parametrize("name", [n for n in shipped() if n.startswith("labs/")])
def test_labs_never_mention_a_swap(name: str) -> None:
    assert " swap" not in words((ROOT / name).read_text(encoding="utf-8"))


def test_ordinary_words_are_not_spoilers() -> None:
    assert spoilers_in("Book HYD to BLR. The keys are swapped. Swap the two key values.") == []
