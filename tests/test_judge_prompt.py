import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPT = (ROOT / "evals" / "judge_prompt.md").read_text(encoding="utf-8")
EVALUATOR = (ROOT / "evals" / "booking_matches.py").read_text(encoding="utf-8")


def test_the_judge_gets_the_evaluator_validity_rules() -> None:
    assert 'IATA = re.compile(r"^[A-Z]{3}$")' in EVALUATOR
    assert "date.fromisoformat(value)" in EVALUATOR
    for rule in (
        "exactly three letters A to Z",
        "real calendar date written YYYY-MM-DD",
        "even when both sides hold the same invalid value",
        "Ignore spaces around a value",
    ):
        assert rule in PROMPT, rule


def test_the_prompt_examples_are_invalid_for_the_evaluator() -> None:
    cases = json.loads((ROOT / "tests" / "eval_cases.json").read_text(encoding="utf-8"))
    invalid = json.dumps(cases)
    for example in ("HYDE", "2026-02-30"):
        assert example in PROMPT
        assert example in invalid
