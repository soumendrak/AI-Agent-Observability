import math
from collections.abc import Sequence


def runs(count: int) -> str:
    return "1 run" if count == 1 else f"{count} runs"


def nearest_rank(seconds: Sequence[float], percent: int) -> float:
    ordered = sorted(seconds)
    return ordered[math.ceil(percent / 100 * len(ordered)) - 1]


def summary(seconds: Sequence[float]) -> str:
    if not seconds:
        raise ValueError("no runs to summarise")
    count = len(seconds)
    p50, p95, p99 = (nearest_rank(seconds, q) for q in (50, 95, 99))
    note = "; under 100 runs p99 is just the slowest run" if count < 100 else ""
    return (
        f"latency over {runs(count)}: mean {sum(seconds) / count:.2f}s, p50 {p50:.2f}s, "
        f"p95 {p95:.2f}s, p99 {p99:.2f}s (nearest rank{note})"
    )
