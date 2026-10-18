import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from tripmate.checkout import TAG

ROOT = Path(__file__).resolve().parent.parent
GUARDS = "src/tripmate/guards.py"
EDIT = 'EARLY_ATTEMPT = "tried Lab 4 at home"'
NOTE = "my notes from the setup email"
STASH = ("git", "stash", "push", "--include-untracked", "-m", "before-workshop")
EMAIL_3 = (
    STASH,
    ("git", "fetch", "--tags"),
    ("git", "checkout", TAG),
    ("uv", "sync"),
    ("uv", "run", "ws", "doctor"),
)
IDENTITY = ("-c", "user.name=freeze-check", "-c", "user.email=freeze-check@example.invalid")
CLEARED = ("VIRTUAL_ENV", "UV_PYTHON", "LLM_MODE")


@dataclass(frozen=True)
class Outcome:
    failed: list[str]
    head: str
    tag: str
    dirty: str
    doctor: str
    stashes: str
    stashed_guards: str = ""
    stashed_note: str = ""


def problems(outcome: Outcome, edited: bool) -> list[str]:
    found = [f"`{command}` failed" for command in outcome.failed]
    if outcome.head != outcome.tag:
        found.append(f"HEAD is not on {TAG}")
    if outcome.dirty:
        found.append(f"files changed after the switch: {outcome.dirty}")
    lines = outcome.doctor.splitlines()
    if not lines or not lines[-1].startswith("READY-"):
        found.append("doctor did not end with a READY code")
    for expected in ("[OK] guards.py is the original", f"[OK] on the workshop version {TAG}"):
        if expected not in lines:
            found.append(f"doctor did not print: {expected}")
    found += [f"doctor printed: {line}" for line in lines if line.startswith(("[WARN]", "[FAIL]"))]
    if not edited:
        return found + ([f"unexpected stash: {outcome.stashes}"] if outcome.stashes else [])
    if "before-workshop" not in outcome.stashes:
        found.append("no before-workshop stash")
    if EDIT not in outcome.stashed_guards:
        found.append("the stash lost the guards.py edit")
    if NOTE not in outcome.stashed_note:
        found.append("the stash lost the untracked file")
    return found


@dataclass
class Machine:
    env: dict[str, str]
    log: list[str] = field(default_factory=list)

    def run(self, cwd: Path, *command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        program = shutil.which(command[0]) or command[0]
        done = subprocess.run(
            [program, *command[1:]],
            cwd=cwd,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            check=False,
        )
        self.log.append(
            f"$ {' '.join(command)}  (exit {done.returncode})\n{done.stdout}{done.stderr}"
        )
        if check and done.returncode:
            raise RuntimeError(f"setup step failed: {' '.join(command)}\n{done.stderr}")
        return done

    def git(self, cwd: Path, *args: str) -> str:
        return self.run(cwd, "git", *IDENTITY, *args).stdout.strip()


def resolve(machine: Machine, ref: str) -> str:
    found = machine.run(
        ROOT, "git", "rev-parse", "-q", "--verify", f"{ref}^{{commit}}", check=False
    )
    return found.stdout.strip() if found.returncode == 0 else ""


def prepare(machine: Machine, clone: Path, env_file: str, edited: bool) -> None:
    (clone / ".env").write_text(env_file, encoding="utf-8")
    machine.run(clone, "uv", "sync")
    if edited:
        guards = clone / GUARDS
        guards.write_text(guards.read_text(encoding="utf-8") + f"\n{EDIT}\n", encoding="utf-8")
        (clone / "notes.txt").write_text(NOTE, encoding="utf-8")


def switch(machine: Machine, clone: Path, edited: bool) -> Outcome:
    failed: list[str] = []
    doctor = ""
    for command in EMAIL_3:
        done = machine.run(clone, *command, check=False)
        if done.returncode:
            failed.append(" ".join(command))
        if command[-1] == "doctor":
            doctor = done.stdout
    show = ("git", "show")
    return Outcome(
        failed=failed,
        head=machine.git(clone, "rev-parse", "HEAD"),
        tag=machine.git(clone, "rev-parse", f"{TAG}^{{commit}}"),
        dirty=machine.git(clone, "status", "--porcelain"),
        doctor=doctor,
        stashes=machine.git(clone, "stash", "list"),
        stashed_guards=machine.run(clone, *show, f"stash@{{0}}:{GUARDS}", check=False).stdout,
        stashed_note=machine.run(clone, *show, "stash@{0}^3:notes.txt", check=False).stdout,
    )


def check(start_ref: str, tag_at: str) -> list[str]:
    sys.path.insert(0, str(ROOT / "tests"))
    from fake_langfuse import serve

    fake, server = serve()
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        (work / "empty.gitconfig").write_text("", encoding="utf-8")
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in CLEARED and not k.startswith("LANGFUSE_")
        }
        env["GIT_CONFIG_GLOBAL"] = str(work / "empty.gitconfig")
        machine = Machine(env)
        tagged = resolve(machine, f"refs/tags/{TAG}")
        target = tagged or resolve(machine, tag_at)
        start = resolve(machine, start_ref) or resolve(machine, f"{target}~1")
        print(f"start {start_ref}: {start}; {TAG}: {target} ({'real' if tagged else 'test'} tag)")
        origin = work / "origin.git"
        machine.git(work, "init", "--bare", "-b", "main", str(origin))
        machine.git(ROOT, "push", "-q", str(origin), f"{start}:refs/heads/main")
        env_file = (
            f"LANGFUSE_PUBLIC_KEY=pk-lf-freeze\nLANGFUSE_SECRET_KEY=sk-lf-freeze\n"
            f"LANGFUSE_BASE_URL={fake.url}\nLLM_MODE=fake\n"
        )
        early = {"a-v0.1-clone": False, "b-edited-guards": True}
        for name, edited in early.items():
            machine.git(work, "clone", "-q", str(origin), name)
            prepare(machine, work / name, env_file, edited)
        machine.git(ROOT, "push", "-q", "-f", str(origin), f"{target}:refs/heads/main")
        if tagged:
            machine.git(ROOT, "push", "-q", str(origin), f"refs/tags/{TAG}:refs/tags/{TAG}")
        else:
            machine.git(origin, "tag", "-a", TAG, target, "-m", "freeze-check test tag")
        machine.git(work, "clone", "-q", str(origin), "c-fresh-clone")
        prepare(machine, work / "c-fresh-clone", env_file, edited=False)
        found: list[str] = []
        for name, edited in [*early.items(), ("c-fresh-clone", False)]:
            outcome = switch(machine, work / name, edited)
            found += [f"{name}: {problem}" for problem in problems(outcome, edited)]
        server.shutdown()
        if found:
            print("\n".join(machine.log))
        return found


def main() -> int:
    options = argparse.ArgumentParser(description="Run the email 3 commands from 3 clone states")
    options.add_argument("--start", default=os.environ.get("FREEZE_START") or "v0.1")
    options.add_argument("--tag-at", default=os.environ.get("FREEZE_TAG_AT") or "HEAD")
    args = options.parse_args()
    found = check(args.start, args.tag_at)
    for problem in found:
        print(problem)
    print("FREEZE CHECK FAILED" if found else "FREEZE CHECK OK")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
