from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

_HERE = Path(__file__).resolve().parent
_CANDIDATES = (_HERE.parents[1] / "evals", _HERE / "evals")
EVALUATOR = next(
    d / "booking_matches.py" for d in _CANDIDATES if (d / "booking_matches.py").is_file()
)


@dataclass
class ObservationContext:
    input: object = None
    output: object = None
    metadata: object = None


@dataclass
class EvaluationContext:
    observation: ObservationContext
    experiment: object = None


@dataclass
class Score:
    name: str
    value: bool
    data_type: str
    comment: str | None = None


@dataclass
class EvaluationResult:
    scores: list[Score]


Evaluate = Callable[[EvaluationContext], EvaluationResult]


def _load_evaluator() -> Evaluate:
    namespace: dict[str, object] = {
        "EvaluationContext": EvaluationContext,
        "EvaluationResult": EvaluationResult,
        "Score": Score,
    }
    code = compile(EVALUATOR.read_text(encoding="utf-8"), str(EVALUATOR), "exec")
    exec(code, namespace)
    return cast(Evaluate, namespace["evaluate"])


def booking_matches_request(observation_input: object, observation_output: object) -> Score:
    context = EvaluationContext(ObservationContext(observation_input, observation_output))
    return _load_evaluator()(context).scores[0]
