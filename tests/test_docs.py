import ast
import re
import shlex
from collections.abc import Iterator
from pathlib import Path

import pytest

from tripmate import cli

ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted([ROOT / "README.md", *ROOT.glob("docs/*.md"), *ROOT.glob("labs/*.md")])
COMMAND = re.compile(r"uv run ws ([^`\n]*)")
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
ANCHOR = re.compile(r"\]\(([^)#\s]*)#([^)\s]+)\)")
EXTERNAL = ("http://", "https://", "mailto:")
LINK_TARGET = re.compile(r"\]\([^)]*\)")


def commands(doc: Path) -> list[str]:
    return [m.group(1).strip() for m in COMMAND.finditer(doc.read_text(encoding="utf-8"))]


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.relative_to(ROOT).as_posix())
def test_every_documented_ws_command_parses(doc: Path) -> None:
    for command in commands(doc):
        cli.parser().parse_args(shlex.split(command))


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.relative_to(ROOT).as_posix())
def test_relative_links_point_at_files(doc: Path) -> None:
    for target in LINK.findall(doc.read_text(encoding="utf-8")):
        if not target.startswith(EXTERNAL):
            assert (doc.parent / target).exists(), f"{doc.name} links to missing {target}"


def slug(heading: str) -> str:
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(doc: Path) -> set[str]:
    text = doc.read_text(encoding="utf-8")
    return {slug(line.lstrip("#")) for line in text.splitlines() if line.startswith("#")}


def missing_anchors(doc: Path) -> list[str]:
    missing: list[str] = []
    for target, anchor in ANCHOR.findall(doc.read_text(encoding="utf-8")):
        if target.startswith(EXTERNAL):
            continue
        if anchor not in anchors((doc.parent / target) if target else doc):
            missing.append(f"{target}#{anchor}")
    return missing


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.relative_to(ROOT).as_posix())
def test_anchor_links_point_at_headings(doc: Path) -> None:
    assert missing_anchors(doc) == []


def test_external_fragments_are_not_local_anchors(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text(
        "# Top\n[a](https://langfuse.com/docs#section) [b](#top) [c](#nowhere)\n",
        encoding="utf-8",
    )
    assert missing_anchors(doc) == ["#nowhere"]


def test_slugs_follow_github() -> None:
    assert slug(" Lab 4: your `guards.py` edit") == "lab-4-your-guardspy-edit"
    assert slug("Setup (about 15 minutes)") == "setup-about-15-minutes"


def test_setup_time_is_the_same_everywhere() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    setup = (ROOT / "labs" / "00-setup.md").read_text(encoding="utf-8")
    assert "## Setup (about 15 minutes)" in readme
    visible = LINK_TARGET.sub("]", setup)
    assert "about 15 minutes" in visible
    assert "5 minutes" not in visible.replace("15 minutes", "")
    assert "5 minutes" not in readme.replace("15 minutes", "")


def test_readme_covers_the_five_minute_setup() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert {"doctor", 'run "Book HYD to BLR on 2026-10-31"', "case 0 --exporter console"} <= set(
        commands(ROOT / "README.md")
    )
    for needed in ("uv sync", "Copy-Item .env.example .env", "cp .env.example .env", "pair"):
        assert needed in readme


MESSAGE = re.compile(r"`((?:\[FAIL\]|\[WARN\]|error:|guard:|trace:) [^`]+)`")
PRINTED_AS = {
    "checkout": (),
    "cli": ("error: ",),
    "doctor": ("[FAIL] ",),
    "models": ("error: ", "[FAIL] "),
    "request": ("error: ",),
    "telemetry.Telemetry.trace_url": ("trace: ",),
    "telemetry.load_env": ("error: ", "[FAIL] "),
    "telemetry.from_env": ("error: ",),
    "tools": ("error: ", "guard: "),
}
SHORTEST_TEXT = 8


Parts = list[str | None]


def strings_in(node: ast.AST) -> Iterator[Parts]:
    for child in ast.walk(node):
        if isinstance(child, ast.JoinedStr):
            yield [
                v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else None
                for v in child.values
            ]
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            yield [child.value]


def emitters(path: Path) -> Iterator[tuple[str, ast.AST]]:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, ast.FunctionDef):
                    yield f"{path.stem}.{node.name}.{method.name}", method
        elif isinstance(node, ast.FunctionDef):
            yield f"{path.stem}.{node.name}", node
        else:
            yield path.stem, node


def source_strings(prefix: str | None = None) -> list[Parts]:
    found: list[Parts] = []
    for path in sorted((ROOT / "src" / "tripmate").glob("*.py")):
        for name, node in emitters(path):
            prefixes = PRINTED_AS.get(name, PRINTED_AS.get(name.split(".", 1)[0], ()))
            if prefix is None or prefix in prefixes:
                found += strings_in(node)
    return [p for p in found if sum(len(t) for t in p if t) >= SHORTEST_TEXT]


def could_print(parts: Parts, message: str) -> bool:
    if not message:
        return True
    if not parts:
        return False
    head, rest = parts[0], parts[1:]
    if head is None:
        word = len(message) if not rest else len(message.split(" ", 1)[0])
        return any(could_print(rest, message[end:]) for end in range(1, word + 1))
    if message.startswith(head):
        return could_print(rest, message[len(head) :])
    return head.startswith(message)


def documented_messages() -> list[str]:
    found: list[str] = []
    for doc in (ROOT / "README.md", ROOT / "docs" / "troubleshooting.md"):
        found += [m.removesuffix("...") for m in MESSAGE.findall(doc.read_text(encoding="utf-8"))]
    return found


def test_common_errors_cover_the_beginner_failures() -> None:
    messages = documented_messages()
    for needed in (
        "these keys belong to the",
        "LANGFUSE_BASE_URL must stop after the host",
        ".env is not UTF-8 text",
        "guard: error in guards.py",
        "guards.py could not be loaded",
        "guards.py differs from the workshop version",
        "not on the workshop version",
        "cannot reach",
        "the keys are swapped",
    ):
        assert any(needed in m for m in messages), needed


def printable(message: str) -> bool:
    prefix = message.split(" ", 1)[0] + " "
    bare = message.removeprefix(prefix)
    return any(could_print(p, message) for p in source_strings()) or any(
        could_print(p, bare) for p in source_strings(prefix)
    )


def test_quoted_messages_are_what_the_code_prints() -> None:
    for message in documented_messages():
        assert printable(message), message


def test_the_prefix_must_be_the_printed_one() -> None:
    assert printable("error: guards.py could not be loaded: NameError")
    assert not printable("[FAIL] guards.py could not be loaded: NameError")
    assert printable("[FAIL] no .env here")
    assert not printable("error: no .env here")
    assert not printable("guard: no .env here")
    assert printable("error: missing LANGFUSE_PUBLIC_KEY")
    assert not printable("[FAIL] missing LANGFUSE_PUBLIC_KEY")
    assert printable("[FAIL] .env is not UTF-8 text")
    assert printable("trace: unavailable (UnauthorizedError)")
    assert not printable("trace: missing LANGFUSE_PUBLIC_KEY")


def test_bare_prefixes_prove_nothing() -> None:
    assert not any(could_print(p, "Failed to spawn: ws") for p in source_strings())


def test_readme_common_errors_match_troubleshooting() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    table = readme.split("## Common errors", 1)[1].split("\n## ", 1)[0]
    guide = (ROOT / "docs" / "troubleshooting.md").read_text(encoding="utf-8")
    quoted = MESSAGE.findall(table)
    assert len(quoted) >= 8
    assert all(f"`{m}" in guide for m in quoted)
    assert "docs/troubleshooting.md" in table


def test_message_matching_is_strict() -> None:
    parts: Parts = ["Langfuse at ", None, " rejected the keys (HTTP ", None, ")"]
    assert could_print(parts, "Langfuse at https://x rejected the keys (HTTP 401)")
    assert could_print(parts, "Langfuse at https://x rejected")
    assert not could_print(parts, "Langfuse at https://x accepted the keys")
    assert not could_print(["no .env here"], "no .env here at all")
