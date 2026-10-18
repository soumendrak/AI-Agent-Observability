import pytest

from tripmate.latency import nearest_rank, summary


def test_fifty_runs_put_p99_on_the_slowest_run() -> None:
    seconds = [n / 100 for n in range(50, 0, -1)]
    assert [nearest_rank(seconds, q) for q in (50, 95, 99)] == [0.25, 0.48, 0.50]
    assert summary(seconds) == (
        "latency over 50 runs: mean 0.26s, p50 0.25s, p95 0.48s, p99 0.50s "
        "(nearest rank; with 50 runs p99 is just the slowest run)"
    )


def test_one_slow_run_moves_the_mean_but_not_the_median() -> None:
    seconds = [1.0] * 199 + [30.0]
    assert summary(seconds) == (
        "latency over 200 runs: mean 1.15s, p50 1.00s, p95 1.00s, p99 1.00s (nearest rank)"
    )


def test_a_single_run() -> None:
    assert nearest_rank([0.4], 99) == 0.4


def test_no_runs() -> None:
    with pytest.raises(ValueError, match="no runs"):
        summary([])
