import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from conftest import ORIGINAL, commit, git

from tripmate import checkout
from tripmate.checkout import TAG

EDITED_WARNING = (
    "[WARN] guards.py differs from the workshop version; if Lab 4 hasn't started, save your "
    'edit with: git stash push --include-untracked -m "before-workshop"'
)
SWITCH = (
    'git stash push --include-untracked -m "before-workshop", then git fetch --tags, then '
    f"git checkout {TAG}, then uv sync"
)
OFF_TAG_WARNING = f"[WARN] not on the workshop version {TAG}; run: {SWITCH}"
DUBIOUS = (
    "fatal: detected dubious ownership in repository at '/home/me/AI-Agent-Observability'\n"
    "To add an exception for this directory, call:\n\n"
    "\tgit config --global --add safe.directory /home/me/AI-Agent-Observability\n"
)


def fake_git(monkeypatch: pytest.MonkeyPatch, answer: object) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def run(command: list[str], **options: object) -> object:
        calls.append(options)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(subprocess, "run", run)
    return calls


def test_original_guards_before_the_tag_exists(clone: Path) -> None:
    assert checkout.review(clone / "guards.py") == ["[OK] guards.py is the original"]


def test_edited_guards_is_flagged(clone: Path) -> None:
    (clone / "guards.py").write_text(ORIGINAL + "    raise ValueError\n", encoding="utf-8")
    assert checkout.review(clone / "guards.py") == [EDITED_WARNING]


def test_on_the_workshop_tag(clone: Path) -> None:
    git(clone, "tag", TAG)
    assert checkout.review(clone / "guards.py") == [
        "[OK] guards.py is the original",
        f"[OK] on the workshop version {TAG}",
    ]


def test_on_a_different_version(clone: Path) -> None:
    git(clone, "tag", TAG)
    commit(clone, ORIGINAL, "later")
    assert checkout.review(clone / "guards.py") == [
        "[OK] guards.py is the original",
        OFF_TAG_WARNING,
    ]


def test_committed_edit_is_compared_with_the_tag(clone: Path) -> None:
    git(clone, "tag", TAG)
    commit(clone, ORIGINAL + "    raise ValueError\n", "my fix")
    assert checkout.review(clone / "guards.py") == [EDITED_WARNING, OFF_TAG_WARNING]


def test_not_a_git_clone(tmp_path: Path) -> None:
    (tmp_path / "guards.py").write_text(ORIGINAL, encoding="utf-8")
    assert checkout.review(tmp_path / "guards.py") == [
        "[WARN] this folder is not a git clone, so the final-version steps won't work; "
        "get the code with: git clone https://github.com/soumendrak/AI-Agent-Observability"
    ]


def test_git_not_installed(clone: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checkout, "which", lambda name: None)
    assert checkout.review(clone / "guards.py") == [
        "[WARN] git was not found, so doctor can't check guards.py or the workshop version; "
        "install git from https://git-scm.com"
    ]


def test_a_hanging_git_is_a_warning(clone: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_git(monkeypatch, subprocess.TimeoutExpired(["git"], 10))
    assert checkout.review(clone / "guards.py") == [
        "[WARN] git did not answer (TimeoutExpired), so doctor couldn't check guards.py or the "
        "workshop version; run uv run ws doctor again"
    ]
    assert calls[0]["timeout"] == 10


def test_git_that_cannot_start_is_a_warning(clone: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_git(monkeypatch, PermissionError("denied"))
    assert checkout.review(clone / "guards.py")[0].startswith(
        "[WARN] git did not answer (PermissionError)"
    )


def test_bytes_that_are_not_utf8_do_not_crash(clone: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real = subprocess.run
    garbage = [sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes([255, 254]))"]

    def run(
        command: list[str],
        *,
        capture_output: bool,
        encoding: str,
        errors: str,
        timeout: float,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        return real(
            garbage,
            capture_output=capture_output,
            encoding=encoding,
            errors=errors,
            timeout=timeout,
            check=check,
        )

    monkeypatch.setattr(subprocess, "run", run)
    assert checkout.review(clone / "guards.py") == [
        "[OK] guards.py is the original",
        f"[OK] on the workshop version {TAG}",
    ]


def test_dubious_ownership_gets_the_safe_directory_fix(
    clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git(monkeypatch, subprocess.CompletedProcess(["git"], 128, "", DUBIOUS))
    assert checkout.review(clone / "guards.py") == [
        "[WARN] git won't read this folder because another user owns it; run: "
        "git config --global --add safe.directory /home/me/AI-Agent-Observability"
    ]


def test_missing_tag_is_flagged_after_the_freeze(
    clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checkout, "now", lambda: checkout.FREEZE)
    assert checkout.review(clone / "guards.py") == [
        "[OK] guards.py is the original",
        f"[WARN] {TAG} isn't in this clone; run: {SWITCH}",
    ]


def test_missing_tag_is_quiet_before_the_freeze(
    clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checkout, "now", lambda: checkout.FREEZE - timedelta(seconds=1))
    assert checkout.review(clone / "guards.py") == ["[OK] guards.py is the original"]


def test_freeze_is_thursday_evening_in_india() -> None:
    assert checkout.FREEZE.isoformat() == "2026-10-29T18:00:00+05:30"
    assert checkout.now().tzinfo == checkout.FREEZE.tzinfo
    assert isinstance(checkout.now(), datetime)
