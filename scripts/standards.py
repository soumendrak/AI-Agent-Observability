import ast
import io
import subprocess
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_COMMENTS = {("src/tripmate/guards.py", "# >>> WORKSHOP EDIT HERE (Lab 4) <<<")}
ALLOWED_DOCSTRINGS = {("src/tripmate/guards.py", "validate_booking")}

DocNode = ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


def repo_files(suffix: str) -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", f"*{suffix}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [ROOT / name for name in listed if (ROOT / name).is_file()]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def comment_problems(path: Path) -> Iterator[str]:
    source = path.read_text(encoding="utf-8")
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if (
            token.type == tokenize.COMMENT
            and (relative(path), token.string) not in ALLOWED_COMMENTS
        ):
            yield f"{relative(path)}:{token.start[0]}: comment"


def docstring_problems(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, DocNode) or ast.get_docstring(node) is None:
            continue
        name = getattr(node, "name", "<module>")
        if (relative(path), name) not in ALLOWED_DOCSTRINGS:
            yield f"{relative(path)}:{getattr(node, 'lineno', 1)}: docstring in {name}"


def any_problems(path: Path) -> Iterator[str]:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        imported = isinstance(node, ast.ImportFrom) and any(a.name == "Any" for a in node.names)
        if imported or (isinstance(node, ast.Attribute) and node.attr == "Any"):
            yield f"{relative(path)}:{getattr(node, 'lineno', 1)}: typing.Any"


def source_problems() -> list[str]:
    problems: list[str] = []
    for path in repo_files(".py"):
        problems += comment_problems(path)
        problems += docstring_problems(path)
        problems += any_problems(path)
    return problems


def run(*command: str) -> bool:
    print(f"$ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=ROOT, check=False).returncode == 0


def main() -> int:
    problems = source_problems()
    for problem in problems:
        print(problem)
    print(f"no-comments and no-Any: {len(problems)} problem(s)")
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
