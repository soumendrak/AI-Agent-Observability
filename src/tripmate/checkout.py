import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import which

TAG = "v2026.10.31"
GUARDS = Path(__file__).with_name("guards.py")
REPO = "https://github.com/soumendrak/AI-Agent-Observability"
IST = timezone(timedelta(hours=5, minutes=30))
FREEZE = datetime(2026, 10, 29, 18, 0, tzinfo=IST)
SWITCH = (
    'git stash push --include-untracked -m "before-workshop", then git fetch --tags, then '
    f"git checkout {TAG}, then uv sync"
)


def now() -> datetime:
    return datetime.now(IST)


def _unreadable(stderr: str) -> str:
    if "dubious ownership" not in stderr:
        return (
            "[WARN] this folder is not a git clone, so the final-version steps won't work; "
            f"get the code with: git clone {REPO}"
        )
    fix = next(
        (line.strip() for line in stderr.splitlines() if "safe.directory" in line),
        "git config --global --add safe.directory <this folder>",
    )
    return f"[WARN] git won't read this folder because another user owns it; run: {fix}"


def _review(git: str, guards: Path) -> list[str]:
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [git, "-C", str(guards.parent), *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )

    top = run("rev-parse", "--show-toplevel")
    if top.returncode:
        return [_unreadable(top.stderr)]
    if run("ls-files", "--error-unmatch", guards.name).returncode:
        return [_unreadable("")]
    tag = run("rev-parse", "-q", "--verify", f"refs/tags/{TAG}^{{commit}}")
    ref = TAG if tag.returncode == 0 else "HEAD"
    lines = (
        [
            "[WARN] guards.py differs from the workshop version; if Lab 4 hasn't started, save "
            'your edit with: git stash push --include-untracked -m "before-workshop"'
        ]
        if run("diff", "--quiet", ref, "--", guards.name).returncode
        else ["[OK] guards.py is the original"]
    )
    if tag.returncode:
        return (
            [*lines, f"[WARN] {TAG} isn't in this clone yet; once it is published, run: {SWITCH}"]
            if now() >= FREEZE
            else lines
        )
    if run("rev-parse", "HEAD").stdout == tag.stdout:
        return [*lines, f"[OK] on the workshop version {TAG}"]
    return [*lines, f"[WARN] not on the workshop version {TAG}; run: {SWITCH}"]


def review(guards: Path) -> list[str]:
    git = which("git")
    if git is None:
        return [
            "[WARN] git was not found, so doctor can't check guards.py or the workshop version; "
            "install git from https://git-scm.com"
        ]
    try:
        return _review(git, guards)
    except (OSError, subprocess.SubprocessError) as error:
        return [
            f"[WARN] git did not answer ({type(error).__name__}), so doctor couldn't check "
            "guards.py or the workshop version; run uv run ws doctor again"
        ]
