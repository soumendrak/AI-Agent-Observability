import ast
import io
import subprocess
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_COMMENTS = {("src/tripmate/guards.py", 1, "# >>> WORKSHOP EDIT HERE (Lab 4) <<<")}
ALLOWED_DOCSTRINGS = {("src/tripmate/guards.py", "validate_booking")}

Definition = ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


def repo_files(suffix: str) -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", f"*{suffix}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\0")
    return [ROOT / name for name in listed if name and (ROOT / name).is_file()]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def comment_problems(path: Path) -> Iterator[str]:
    source = path.read_text(encoding="utf-8")
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        allowed = (relative(path), token.start[0], token.string) in ALLOWED_COMMENTS
        if token.type == tokenize.COMMENT and not allowed:
            yield f"{relative(path)}:{token.start[0]}: comment"


def documented(node: ast.AST, prefix: str) -> Iterator[tuple[str, int]]:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, Definition):
            name = f"{prefix}{child.name}"
            if ast.get_docstring(child) is not None:
                yield name, child.lineno
            yield from documented(child, f"{name}.")
        else:
            yield from documented(child, prefix)


def docstring_problems(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = [("<module>", 1)] if ast.get_docstring(tree) is not None else []
    for name, line in found + list(documented(tree, "")):
        if (relative(path), name) not in ALLOWED_DOCSTRINGS:
            yield f"{relative(path)}:{line}: docstring in {name}"


def source_problems() -> list[str]:
    problems: list[str] = []
    for path in repo_files(".py") + repo_files(".pyi"):
        problems += comment_problems(path)
        problems += docstring_problems(path)
    return problems


def run(*command: str) -> bool:
    print(f"$ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=ROOT, check=False).returncode == 0


def main() -> int:
    problems = source_problems()
    for problem in problems:
        print(problem)
    print(f"no-comments: {len(problems)} problem(s)")
    python = sys.executable
    results = [
        not problems,
        run(python, "-m", "ruff", "format", "--check", "."),
        run(python, "-m", "ruff", "check", "."),
        run(python, "-m", "mypy"),
        run(python, "-m", "pytest", "--cov", "--cov-report=term-missing"),
    ]
    if all(results):
        print("STANDARDS OK")
        return 0
    print("STANDARDS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
