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
    seen: dict[str, int] = {}
    found: set[str] = set()
    for line in text.splitlines():
        if line.startswith("#"):
            base = slug(line.lstrip("#"))
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(f"{base}-{count}" if count else base)
    return found


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


def test_repeated_headings_get_github_suffixes(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("## Steps\n## Steps\n## Steps\n[b](#steps-1) [c](#steps-2)\n", encoding="utf-8")
    assert anchors(doc) == {"steps", "steps-1", "steps-2"}
    assert missing_anchors(doc) == []


def test_slugs_follow_github() -> None:
    assert slug(" Lab 4: your `guards.py` edit") == "lab-4-your-guardspy-edit"
    assert slug("Setup (about 15 minutes)") == "setup-about-15-minutes"


def test_setup_anchor_is_stable() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    setup = (ROOT / "labs" / "00-setup.md").read_text(encoding="utf-8")
    assert "\n## Setup\n" in readme
    assert "../README.md#setup)" in setup


CLOCK_OR_DURATION = re.compile(
    r"\b\d{2}:\d{2}\b"
    r"|\b(?:minutes?|hours?|hrs?|mins?|seconds|secs?)\b"
    r"|\b\d+\s?(?:seconds?|secs?|s|ms|h|hrs?)\b",
    re.IGNORECASE,
)
ALLOWED_TIME_TEXT = re.compile(r"\b\d+\.\d+s\b|after 30 s\b")


def states_a_time(text: str) -> bool:
    return bool(CLOCK_OR_DURATION.search(ALLOWED_TIME_TEXT.sub("", text)))


TIMELESS = [
    ROOT / "README.md",
    ROOT / "docs" / "troubleshooting.md",
    *sorted(ROOT.glob("labs/*.md")),
]


@pytest.mark.parametrize("doc", TIMELESS, ids=lambda p: p.name)
def test_readme_and_labs_state_no_times(doc: Path) -> None:
    assert not states_a_time(doc.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "added",
    [
        "Wait 2 hours.",
        "Wait 30 seconds.",
        "Wait 30s.",
        "Wait 5 min.",
        "It takes 5 minutes.",
        "Start at 09:30.",
        "after 31 s",
    ],
)
def test_the_no_times_check_catches_every_unit(added: str) -> None:
    assert states_a_time(f"Run `uv sync`. {added}")


@pytest.mark.parametrize(
    "allowed",
    [
        "run 1/50: PASS in 0.70s",
        "mean 0.79s, p50 0.71s",
        "after 30 s",
        "the second terminal",
        "an optional second alert",
    ],
)
def test_the_no_times_check_allows_sample_output_and_ordinals(allowed: str) -> None:
    assert not states_a_time(allowed)


CHECK_BEFORE_INSTALL = {
    "uv --version": (
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "wget -qO- https://astral.sh/uv/install.sh | sh",
        "irm https://astral.sh/uv/install.ps1 | iex",
        "winget install --id=astral-sh.uv",
    ),
    "git --version": (
        "xcode-select --install",
        "winget install --id Git.Git",
        "sudo apt-get install git",
        "sudo dnf install git",
    ),
}
SKIP_PHRASES = ("skip to the next step", "skip its install")
CHECK_FIRST_DOCS = [
    ROOT / "README.md",
    ROOT / "docs" / "troubleshooting.md",
    ROOT / "docs" / "integration-gate.md",
]
BOUNDARY = re.compile(r"^(?:#{1,6} |\d+\. )", re.MULTILINE)


def lead_in(text: str, at: int) -> str:
    row_start = text.rfind("\n", 0, at) + 1
    if text[row_start] == "|":
        return text[row_start:at]
    starts = [m.start() for m in BOUNDARY.finditer(text, 0, at)]
    return text[starts[-1] if starts else 0 : at]


def is_gated(lead: str, check: str) -> bool:
    only_if = f"only if `{check}` fails"
    if only_if in lead:
        return True
    return any(check in lead and lead.rfind(phrase) > lead.find(check) for phrase in SKIP_PHRASES)


def ungated_installs(text: str) -> list[str]:
    found: list[str] = []
    for check, installs in CHECK_BEFORE_INSTALL.items():
        for install in installs:
            for match in re.finditer(re.escape(install), text):
                if not is_gated(lead_in(text, match.start()), check):
                    found.append(f"{install} at {match.start()}")
    return found


@pytest.mark.parametrize("doc", CHECK_FIRST_DOCS, ids=lambda p: p.name)
def test_every_install_command_is_gated_by_its_own_check(doc: Path) -> None:
    assert ungated_installs(doc.read_text(encoding="utf-8")) == []


def test_every_doc_that_installs_runs_the_check_first() -> None:
    for doc in CHECK_FIRST_DOCS:
        text = doc.read_text(encoding="utf-8")
        for check, installs in CHECK_BEFORE_INSTALL.items():
            if any(install in text for install in installs):
                assert check in text, f"{doc.name} installs without {check}"


def troubleshooting() -> str:
    return (ROOT / "docs" / "troubleshooting.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("doc", "phrase"),
    [
        ("docs/troubleshooting.md", "only if `uv --version` fails"),
        ("README.md", "If you saw a version number, skip to the next step."),
        ("docs/integration-gate.md", "so skip its install"),
    ],
)
def test_removing_a_gate_phrase_makes_the_check_fail(doc: str, phrase: str) -> None:
    text = (ROOT / doc).read_text(encoding="utf-8")
    assert phrase in text
    assert ungated_installs(text.replace(phrase, "")) != []


def test_a_gate_for_one_tool_does_not_cover_another() -> None:
    row = "| x | only if `uv --version` fails, run `winget install --id Git.Git -e` |"
    assert ungated_installs(row) == [f"winget install --id Git.Git at {row.index('winget')}"]


def test_an_install_in_the_next_row_is_not_gated_by_the_row_above() -> None:
    text = (
        "| a | only if `uv --version` fails, install |\n"
        "| b | `winget install --id=astral-sh.uv -e` |\n"
    )
    assert len(ungated_installs(text)) == 1


def test_a_skip_line_after_the_install_gates_nothing() -> None:
    text = (
        "### Step\n\nuv --version\n\n"
        "curl -LsSf https://astral.sh/uv/install.sh | sh\n\n"
        "skip to the next step\n"
    )
    assert len(ungated_installs(text)) == 1


def readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    return text.split(heading, 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]


def test_readme_covers_every_install_command_for_every_os() -> None:
    body = readme()
    for install in (
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "wget -qO- https://astral.sh/uv/install.sh | sh",
        'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
        "xcode-select --install",
        "winget install --id Git.Git -e --source winget",
        "sudo apt-get install git",
        "sudo dnf install git",
    ):
        assert install in body, install


def test_each_readme_install_is_gated_by_a_skip_line() -> None:
    for heading, check in (("### Step 2.", "git --version"), ("### Step 3.", "uv --version")):
        body = section(readme(), heading)
        skip = body.index("If you saw a version number, skip to the next step.")
        assert "If not, install it" in body
        assert body.index(check) < skip
        assert all(
            skip < body.index(install) for install in CHECK_BEFORE_INSTALL[check] if install in body
        )
        for failure in ("command not found", "is not recognized"):
            assert failure in body


def test_the_wget_fallback_follows_the_curl_install() -> None:
    body = section(readme(), "### Step 3.")
    assert (
        body.index("curl -LsSf") < body.index("curl: command not found") < body.index("wget -qO-")
    )


def test_step_5_pulls_if_the_clone_exists_and_clones_if_it_does_not() -> None:
    body = section(readme(), "### Step 5.")
    check = body.index("git -C AI-Agent-Observability rev-parse --is-inside-work-tree")
    pull = body.index("git pull --ff-only")
    clone = body.index("git clone https://github.com")
    assert check < pull < clone
    done = body.index("You are done with getting the code.")
    assert pull < done < clone
    assert body.index("cd AI-Agent-Observability") < pull
    assert body.count("cd AI-Agent-Observability\n") == 3


def test_step_5_moves_a_non_clone_aside_only_to_a_free_name() -> None:
    body = section(readme(), "### Step 5.")
    for check, move in (
        ("ls AI-Agent-Observability-old", "mv AI-Agent-Observability AI-Agent-Observability-old"),
        (
            "Test-Path AI-Agent-Observability-old",
            "Rename-Item AI-Agent-Observability AI-Agent-Observability-old",
        ),
    ):
        assert body.index(check) < body.index(move) < body.rindex("git clone https://github.com")


def test_env_is_checked_before_it_is_copied() -> None:
    body = readme()
    for check, copy in (
        ("ls .env", "cp .env.example .env"),
        ("Test-Path .env", "Copy-Item .env.example .env"),
    ):
        assert body.index(check) < body.index(copy), copy
    gate = (ROOT / "docs" / "integration-gate.md").read_text(encoding="utf-8")
    assert gate.index("Test-Path .env") < gate.index("Copy-Item .env.example .env")
    assert gate.index("ls .env") < gate.index("cp .env.example .env")
    assert gate.index("git -C gate-check rev-parse") < gate.index("git clone")


def test_the_stash_is_gated_by_a_status_check() -> None:
    body = section(readme(), "## Before the workshop")
    status = body.index("git status --short")
    assert status < body.index("If it prints nothing") < body.index("git stash push")


def test_pull_never_runs_without_ff_only() -> None:
    for doc in CHECK_FIRST_DOCS:
        assert not re.search(r"git pull(?! --ff-only)", doc.read_text(encoding="utf-8")), doc.name


def test_the_ff_only_failure_has_a_row_that_avoids_destructive_commands() -> None:
    row = next(
        line for line in troubleshooting().splitlines() if "Not possible to fast-forward" in line
    )
    assert "ask a ta" in row.lower()
    for destructive in ("reset --hard", "push --force", "clean -f", "rm -rf", "checkout ."):
        assert destructive not in troubleshooting()
        assert destructive not in readme()


def test_the_not_on_a_branch_rows_say_what_to_do_about_local_changes() -> None:
    stash = 'git stash push --include-untracked -m "before-workshop"'
    for text in (readme(), troubleshooting()):
        row = next(
            line for line in text.splitlines() if "You are not currently on a branch" in line
        )
        assert "git checkout main" in row
        assert stash in row
        assert "complains about local changes" in row


def test_the_rename_aside_collision_has_a_troubleshooting_row() -> None:
    row = next(
        line
        for line in troubleshooting().splitlines()
        if line.startswith("|") and "Cannot create a file when that file already exists" in line
    )
    assert "AI-Agent-Observability-old2" in row


def test_the_hidden_file_pointers_have_an_explanation_to_point_at() -> None:
    body = section(readme(), "### Step 6.")
    assert "starts with a dot" in body
    assert "ls -a" in body
    assert "ls -Force" in body
    assert "Use the `ls` command in step 6" not in readme()


def test_readme_does_not_promise_nothing_is_overwritten() -> None:
    assert "nothing gets overwritten" not in readme().lower()
    assert "none of your own files get overwritten if you follow the checks" in readme().lower()


def test_readme_covers_the_five_minute_setup() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert {"doctor", 'run "Book HYD to BLR on 2026-10-31"', "case 0 --exporter console"} <= set(
        commands(ROOT / "README.md")
    )
    for needed in ("uv sync", "Copy-Item .env.example .env", "cp .env.example .env", "pair"):
        assert needed in readme


MESSAGE = re.compile(r"`((?:\[FAIL\]|\[WARN\]|error:|guard:|trace:) [^`]+)`")
PRINTED_AS = {
    "cli:raise": ("error: ",),
    "doctor:yield": ("[OK] ",),
    "doctor:raise": ("[FAIL] ",),
    "doctor._explain:return": ("[FAIL] ",),
    "models:raise": ("error: ", "[FAIL] "),
    "request:raise": ("error: ",),
    "telemetry.Telemetry.trace_url:return": ("trace: ",),
    "telemetry.load_env:raise": ("error: ", "[FAIL] "),
    "telemetry.from_env:raise": ("error: ",),
    "tools:raise": ("error: ",),
    "tools:other": ("guard: ",),
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


EXITS: dict[type[ast.AST], str] = {ast.Yield: "yield", ast.Raise: "raise", ast.Return: "return"}


def emitted(node: ast.AST, kind: str = "other") -> Iterator[tuple[str, Parts]]:
    if isinstance(node, ast.JoinedStr | ast.Constant):
        yield from ((kind, parts) for parts in strings_in(node))
        return
    for child in ast.iter_child_nodes(node):
        yield from emitted(child, EXITS.get(type(child), kind))


def emitters(path: Path) -> Iterator[tuple[str, ast.AST]]:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.ClassDef):
            for method in node.body:
                yield f"{path.stem}.{node.name}.{getattr(method, 'name', '')}", method
        elif isinstance(node, ast.FunctionDef):
            yield f"{path.stem}.{node.name}", node
        else:
            yield path.stem, node


def prefixes_for(name: str, kind: str) -> tuple[str, ...]:
    module = name.split(".", 1)[0]
    return PRINTED_AS.get(f"{name}:{kind}", PRINTED_AS.get(f"{module}:{kind}", ()))


def source_strings(prefix: str | None = None) -> list[Parts]:
    found: list[Parts] = []
    for path in sorted((ROOT / "src" / "tripmate").glob("*.py")):
        for name, node in emitters(path):
            for kind, parts in emitted(node):
                if prefix is None or prefix in prefixes_for(name, kind):
                    found.append(parts)
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
    assert not printable("[FAIL] keys look right")
    assert printable("[FAIL] LANGFUSE_BASE_URL must stop after the host")


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
