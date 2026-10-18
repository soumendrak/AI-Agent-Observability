import argparse
import os
import runpy
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import openai

from tripmate import doctor, models
from tripmate.agent import RunResult, run_agent
from tripmate.cases import CASES
from tripmate.checks import booking_matches_request
from tripmate.console import render
from tripmate.request import EXAMPLE, FIELDS
from tripmate.telemetry import SetupError, Telemetry, console, from_env, load_env
from tripmate.tools import Guard, no_guard

GUARDS_FILE = Path(__file__).with_name("guards.py")
Model = models.RealModel | None


def load_guard(mode: str) -> Guard:
    if mode == "off":
        return no_guard
    try:
        names = runpy.run_path(str(GUARDS_FILE))
    except SyntaxError as error:
        raise SetupError(f"guards.py line {error.lineno}: {error.msg}") from error
    except Exception as error:
        raise SetupError(
            f"guards.py could not be loaded: {type(error).__name__}: {error}"
        ) from error
    guard = names.get("validate_booking")
    if not callable(guard):
        raise SetupError("guards.py must define validate_booking(requested, args)")
    return cast(Guard, guard)


def guard_outcome(result: RunResult, mode: str) -> str:
    if mode == "off":
        return "guard: off"
    if result.guard_error:
        return f"guard: {result.guard_error}"
    if result.rejected:
        rejected = result.rejected[0]
        wrong = [f for f in FIELDS if rejected.get(f) != result.requested.get(f)]
        return f"guard: caught mismatch on {', '.join(wrong)}"
    if result.booking and any(result.booking[f] != result.requested[f] for f in FIELDS):
        return "guard: no-op"
    return "guard: did not reject anything"


def local_check(result: RunResult) -> str:
    if result.guard_error:
        return "booking_matches_request: not checked; fix the error in guards.py first"
    score = booking_matches_request({"requested": result.requested}, result.output)
    verdict = "PASS" if score.value else f"FAIL: {score.comment}"
    return f"booking_matches_request: {verdict} (local check, same logic as the Langfuse evaluator)"


def report(
    args: argparse.Namespace, telemetry: Telemetry, case: int, text: str, model: Model
) -> None:
    result = run_agent(
        text, case, load_guard(args.guard), telemetry, sdk_score=args.score == "sdk", model=model
    )
    if telemetry.memory is not None:
        print(render(telemetry.spans(result.trace_id)))
    print(f"TripMate: {result.final_message}")
    if getattr(args, "rerun", False):
        print(guard_outcome(result, args.guard))
    print(f"trace: {telemetry.trace_url(result.trace_id)}")
    if getattr(args, "rerun", False):
        print(local_check(result))


def positive(text: str) -> int:
    number = int(text)
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be 1 or more, got {number}")
    return number


def load(
    args: argparse.Namespace, telemetry: Telemetry, case: int, text: str, model: Model
) -> None:
    guard, passed = load_guard(args.guard), 0
    for run in range(args.n):
        started = time.perf_counter()
        result = run_agent(
            text, case, guard, telemetry, seed=run, sdk_score=args.score == "sdk", model=model
        )
        score = booking_matches_request({"requested": result.requested}, result.output)
        passed += score.value
        verdict = "PASS" if score.value else "FAIL"
        print(f"run {run + 1}/{args.n}: {verdict} in {time.perf_counter() - started:.2f}s")
    print(f"done: {args.n} runs of case {case}, local check PASS {passed}/{args.n}")


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--exporter", choices=["langfuse", "console"], default="langfuse")
    common.add_argument("--guard", choices=["on", "off"], default="on")
    common.add_argument(
        "--score", choices=["none", "sdk"], default="none", help="sdk: send the local check score"
    )
    root = argparse.ArgumentParser(prog="ws", description="TripMate workshop commands")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", parents=[common], help="run TripMate on your own request")
    run.add_argument("text", nargs="?", default=EXAMPLE)
    case = commands.add_parser("case", parents=[common], help="run a workshop case")
    case.add_argument("number", type=int, choices=sorted(CASES))
    case.add_argument("text", nargs="?", default=EXAMPLE)
    case.add_argument("--rerun", action="store_true", help="reload guards.py and check the result")
    commands.add_parser("doctor", help="check your setup and print your READY code")
    many = commands.add_parser("load", parents=[common], help="run a case many times")
    many.add_argument("-n", type=positive, default=50, help="number of runs")
    many.add_argument("--case", dest="number", type=int, choices=sorted(CASES), default=0)
    many.add_argument("text", nargs="?", default=EXAMPLE)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "doctor":
        return doctor.run((sys.version_info.major, sys.version_info.minor))
    try:
        load_env(Path.cwd() / ".env")
        mode = os.environ.get("LLM_MODE", "fake")
        if mode not in ("fake", "openai"):
            raise SetupError(f"LLM_MODE={mode} is not supported; set LLM_MODE=fake in .env")
        case = getattr(args, "number", 0)
        model = models.from_env() if mode == "openai" else None
        if model is not None and case != 0:
            raise SetupError(
                "LLM_MODE=openai runs only case 0; the workshop faults need LLM_MODE=fake"
            )
        if args.score == "sdk" and args.exporter == "console":
            raise SetupError("--score sdk sends scores to Langfuse; drop --exporter console")
        telemetry = console() if args.exporter == "console" else from_env()
        command = load if args.command == "load" else report
        command(args, telemetry, case, args.text, model)
        telemetry.langfuse.flush()
    except (SetupError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except openai.APIError as error:
        print(
            f"error: the model call failed ({type(error).__name__}); check OPENAI_API_KEY, "
            "OPENAI_BASE_URL and OPENAI_MODEL in .env",
            file=sys.stderr,
        )
        return 2
    return 0
