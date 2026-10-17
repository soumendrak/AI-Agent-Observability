import argparse
import os
import runpy
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

from tripmate.agent import RunResult, run_agent
from tripmate.cases import CASES
from tripmate.checks import booking_matches_request
from tripmate.console import render
from tripmate.request import EXAMPLE, FIELDS
from tripmate.telemetry import SetupError, Telemetry, console, from_env
from tripmate.tools import Fields, Guard

GUARDS_FILE = Path(__file__).with_name("guards.py")


def _no_guard(requested: Fields, args: Fields) -> None:
    return None


def load_guard(mode: str) -> Guard:
    if mode == "off":
        return _no_guard
    try:
        return cast(Guard, runpy.run_path(str(GUARDS_FILE))["validate_booking"])
    except SyntaxError as error:
        raise SetupError(f"guards.py line {error.lineno}: {error.msg}") from error


def guard_outcome(result: RunResult, mode: str) -> str:
    if mode == "off":
        return "guard: off"
    if result.rejected:
        rejected = result.rejected[0]
        wrong = [f for f in FIELDS if rejected.get(f) != result.requested.get(f)]
        return f"guard: caught mismatch on {', '.join(wrong)}"
    if result.booking and any(result.booking[f] != result.requested[f] for f in FIELDS):
        return "guard: no-op"
    return "guard: did not reject anything"


def local_check(result: RunResult) -> str:
    score = booking_matches_request({"requested": result.requested}, result.output)
    verdict = "PASS" if score.value else f"FAIL: {score.comment}"
    return f"booking_matches_request: {verdict} (local check, same logic as the Langfuse evaluator)"


def report(args: argparse.Namespace, telemetry: Telemetry, case: int, text: str) -> None:
    result = run_agent(text, case, load_guard(args.guard), telemetry)
    if telemetry.memory is not None:
        print(render(telemetry.spans(result.trace_id)))
    print(f"TripMate: {result.final_message}")
    if getattr(args, "rerun", False):
        print(guard_outcome(result, args.guard))
    print(f"trace: {telemetry.trace_url(result.trace_id)}")
    if getattr(args, "rerun", False):
        print(local_check(result))


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--exporter", choices=["langfuse", "console"], default="langfuse")
    common.add_argument("--guard", choices=["on", "off"], default="on")
    root = argparse.ArgumentParser(prog="ws", description="TripMate workshop commands")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", parents=[common], help="run TripMate on your own request")
    run.add_argument("text", nargs="?", default=EXAMPLE)
    case = commands.add_parser("case", parents=[common], help="run a workshop case")
    case.add_argument("number", type=int, choices=sorted(CASES))
    case.add_argument("text", nargs="?", default=EXAMPLE)
    case.add_argument("--rerun", action="store_true", help="reload guards.py and check the result")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    load_dotenv(Path.cwd() / ".env")
    try:
        mode = os.environ.get("LLM_MODE", "fake")
        if mode != "fake":
            raise SetupError(f"LLM_MODE={mode} is not supported; set LLM_MODE=fake in .env")
        telemetry = console() if args.exporter == "console" else from_env()
        report(args, telemetry, getattr(args, "number", 0), args.text)
        telemetry.langfuse.flush()
    except (SetupError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0
