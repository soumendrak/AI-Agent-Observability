import math
from pathlib import Path

import pytest

DOC = (Path(__file__).resolve().parents[1] / "docs" / "maths-appendix.md").read_text(
    encoding="utf-8"
)
Z = 1.959964
TIMES, MINUS = "\u00d7", "\u2212"


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def bounds(passed: int, runs: int) -> tuple[float, float]:
    share = passed / runs
    scale = 1 + Z * Z / runs
    centre = (share + Z * Z / (2 * runs)) / scale
    half = Z * math.sqrt(share * (1 - share) / runs + Z * Z / (4 * runs * runs)) / scale
    return centre - half, centre + half


def wilson(passed: int, runs: int) -> str:
    low, high = bounds(passed, runs)
    return f"{percent(low)} to {percent(high)}"


def test_difference_interval_is_newcombe() -> None:
    low1, high1 = bounds(44, 50)
    low2, high2 = bounds(46, 50)
    first, second = 44 / 50, 46 / 50
    gap = second - first
    low = gap - math.hypot(second - low2, high1 - first)
    high = gap + math.hypot(high2 - second, first - low1)
    interval = f"{MINUS}{-low * 100:.1f} to +{high * 100:.1f}"
    assert f"{gap * 100:.0f} points, with a 95% interval of {interval}" in DOC
    assert low < 0 < high


def test_example_paths_are_under_chapters() -> None:
    assert "`chapters/ch9-sampling-pii/otel-collector-config.yaml`" in DOC


@pytest.mark.parametrize(("passed", "runs"), [(9, 10), (45, 50), (450, 500), (44, 50), (46, 50)])
def test_wilson_intervals(passed: int, runs: int) -> None:
    assert wilson(passed, runs) in DOC


@pytest.mark.parametrize("steps", [5, 10, 25, 50, 100])
def test_one_slow_step_somewhere(steps: int) -> None:
    assert f"| {steps} | {percent(1 - 0.99**steps)} |" in DOC


def test_the_rest_of_the_numbers() -> None:
    precision = 0.95 * 0.02 / (0.95 * 0.02 + 0.05 * 0.98)
    for claim in (
        f"0.95^10 = {percent(0.95**10)}",
        f"0.99^10 = {percent(0.99**10)}",
        f"pass@3 = 1 {MINUS} 0.3^3 = {percent(1 - 0.3**3)}",
        f"pass^3 = 0.7^3 = {percent(0.7**3)}",
        f"= {precision * 100:.0f}%. At 1,000 runs a day, that's {0.95 * 0.02 * 1000:.0f} true "
        f"alarms and {0.05 * 0.98 * 1000:.0f} false ones",
        f"about {Z * Z * 0.25 / 0.05**2:.0f} for ±5 points",
        f"about {Z * Z * 0.25 / 0.03**2:,.0f} for ±3",
        f"rank ceil(0.99 {TIMES} 50) = {math.ceil(0.99 * 50)}",
        f"0.99 {TIMES} 49 = {0.99 * 49:.2f}",
        f"spends {14.4 / (30 * 24) * 100:.0f}% of a 30-day budget in 1 hour",
        f"up to {3 / 50:.0%}",
    ):
        assert claim in DOC, claim
