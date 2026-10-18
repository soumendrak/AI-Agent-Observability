import subprocess
from pathlib import Path
from shutil import which

TAG = "v2026.10.31"
GUARDS = Path(__file__).with_name("guards.py")
REPO = "https://github.com/soumendrak/AI-Agent-Observability"


def review(guards: Path) -> list[str]:
    git = which("git")
    if git is None:
        return [
            "[WARN] git was not found, so doctor can't check guards.py or the workshop version; "
            "install git from https://git-scm.com"
        ]

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [git, "-C", str(guards.parent), *args], capture_output=True, text=True, check=False
        )

    if run("rev-parse", "--show-toplevel").returncode:
        return [
            "[WARN] this folder is not a git clone, so the final-version steps won't work; "
            f"get the code with: git clone {REPO}"
        ]
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
        return lines
    if run("rev-parse", "HEAD").stdout == tag.stdout:
        return [*lines, f"[OK] on the workshop version {TAG}"]
    return [
        *lines,
        f"[WARN] not on the workshop version {TAG}; run: git fetch --tags, then "
        f"git checkout {TAG}, then uv sync",
    ]
