import ast
import io
import re
import subprocess
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_COMMENTS = {("src/tripmate/guards.py", 1, "# >>> WORKSHOP EDIT HERE (Lab 4) <<<")}
ALLOWED_DOCSTRINGS = {("src/tripmate/guards.py", "validate_booking")}

EVALUATOR = ROOT / "evals" / "booking_matches.py"
TYPED_EVALUATOR = ROOT / ".standards" / "booking_matches_typed.py"
CONTRACT_IMPORT = "from tripmate.checks import EvaluationContext, EvaluationResult, Score\n"
TS_BANNED = re.compile(r"//|/\*|\bany\b")
TSC = ROOT / "node_modules" / "typescript" / "bin" / "tsc"
TS_PARITY = ROOT / ".ts-build" / "tests" / "ts" / "parity.js"

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


def documented(body: list[ast.stmt], prefix: str) -> Iterator[tuple[str, int]]:
    for node in body:
        if isinstance(node, Definition):
            name = f"{prefix}{node.name}"
            if ast.get_docstring(node) is not None:
                yield name, node.lineno
            yield from documented(node.body, f"{name}.")


def docstring_problems(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = [("<module>", 1)] if ast.get_docstring(tree) is not None else []
    for name, line in found + list(documented(tree.body, "")):
        if (relative(path), name) not in ALLOWED_DOCSTRINGS:
            yield f"{relative(path)}:{line}: docstring in {name}"


def any_problems(path: Path) -> Iterator[str]:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        imported = isinstance(node, ast.ImportFrom) and any(a.name == "Any" for a in node.names)
        if imported or (isinstance(node, ast.Attribute) and node.attr == "Any"):
            yield f"{relative(path)}:{getattr(node, 'lineno', 1)}: typing.Any"


def source_problems() -> list[str]:
    problems: list[str] = []
    for path in repo_files(".ts"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if TS_BANNED.search(line):
                problems.append(f"{relative(path)}:{number}: comment or any in TypeScript")
    for path in repo_files(".py"):
        problems += comment_problems(path)
        problems += docstring_problems(path)
        problems += any_problems(path)
    return problems


def run(*command: str) -> bool:
    print(f"$ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=ROOT, check=False).returncode == 0


def typed_evaluator() -> str:
    TYPED_EVALUATOR.parent.mkdir(exist_ok=True)
    imports, body = EVALUATOR.read_text(encoding="utf-8").split("\n\n", 1)
    TYPED_EVALUATOR.write_text(f"{imports}\n\n{CONTRACT_IMPORT}\n{body}", "utf-8")
    return str(TYPED_EVALUATOR)


def typescript() -> bool:
    if not TSC.is_file():
        print("TypeScript: node_modules missing, run `npm ci` first")
        return False
    return run("node", str(TSC), "-p", "tsconfig.json") and run("node", str(TS_PARITY))


def main() -> int:
    problems = source_problems()
    for problem in problems:
        print(problem)
    print(f"no-comments and no-Any: {len(problems)} problem(s)")
    python = sys.executable
    results = [
        not problems,
        run(python, "-m", "ruff", "format", "--check", ".", str(EVALUATOR)),
        run(python, "-m", "ruff", "check", ".", typed_evaluator()),
        run(python, "-m", "mypy"),
        run(python, "-m", "mypy", typed_evaluator()),
        typescript(),
        run(python, "-m", "pytest", "--cov", "--cov-report=term-missing"),
    ]
    if all(results):
        print("STANDARDS OK")
        return 0
    print("STANDARDS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
