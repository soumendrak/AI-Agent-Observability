from pathlib import Path

import pytest
from conftest import ORIGINAL, commit, git

from tripmate import checkout
from tripmate.checkout import TAG

EDITED_WARNING = (
    "[WARN] guards.py differs from the workshop version; if Lab 4 hasn't started, save your "
    'edit with: git stash push --include-untracked -m "before-workshop"'
)
OFF_TAG_WARNING = (
    f"[WARN] not on the workshop version {TAG}; run: git fetch --tags, then "
    f"git checkout {TAG}, then uv sync"
)


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
