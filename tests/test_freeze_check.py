from dataclasses import replace

import pytest
from freeze_check import EDIT, NOTE, Outcome, problems

from tripmate.checkout import TAG

DOCTOR = "\n".join(
    [
        "[OK] Python 3.12",
        "[OK] guards.py is the original",
        f"[OK] on the workshop version {TAG}",
        "[OK] hello trace: http://127.0.0.1/project/p/traces/t",
        "READY-1A2B",
    ]
)
CLEAN = Outcome(failed=[], head="abc", tag="abc", dirty="", doctor=DOCTOR, stashes="")
EDITED = replace(
    CLEAN,
    stashes="stash@{0}: On main: before-workshop",
    stashed_guards=f"def validate_booking():\n    return\n{EDIT}\n",
    stashed_note=NOTE,
)


def test_a_clean_switch_has_no_problems() -> None:
    assert problems(CLEAN, edited=False) == []
    assert problems(EDITED, edited=True) == []


@pytest.mark.parametrize(
    ("outcome", "edited", "expected"),
    [
        (replace(CLEAN, failed=["uv sync"]), False, "`uv sync` failed"),
        (replace(CLEAN, head="old"), False, f"HEAD is not on {TAG}"),
        (
            replace(CLEAN, dirty=" M src/tripmate/guards.py"),
            False,
            "files changed after the switch:  M src/tripmate/guards.py",
        ),
        (
            replace(CLEAN, doctor=DOCTOR.replace("READY-1A2B", "")),
            False,
            "doctor did not end with a READY code",
        ),
        (
            replace(CLEAN, doctor=DOCTOR.replace(f"[OK] on the workshop version {TAG}\n", "")),
            False,
            f"doctor did not print: [OK] on the workshop version {TAG}",
        ),
        (
            replace(CLEAN, doctor="[WARN] guards.py differs\n" + DOCTOR),
            False,
            "doctor printed: [WARN] guards.py differs",
        ),
        (replace(EDITED, stashes=""), True, "no before-workshop stash"),
        (
            replace(EDITED, stashed_guards="def validate_booking():\n    return\n"),
            True,
            "the stash lost the guards.py edit",
        ),
        (replace(EDITED, stashed_note=""), True, "the stash lost the untracked file"),
        (
            replace(CLEAN, stashes="stash@{0}: On main: x"),
            False,
            "unexpected stash: stash@{0}: On main: x",
        ),
    ],
)
def test_each_broken_promise_is_reported(outcome: Outcome, edited: bool, expected: str) -> None:
    assert expected in problems(outcome, edited=edited)
