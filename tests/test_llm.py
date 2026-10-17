from tripmate.llm import ScriptedFakeLLM


def test_latency_is_seeded() -> None:
    first = [ScriptedFakeLLM(seed=7).latency() for _ in range(3)]
    again = [ScriptedFakeLLM(seed=7).latency() for _ in range(3)]
    assert first == again


def test_latency_has_a_tail() -> None:
    llm = ScriptedFakeLLM(seed=1)
    draws = [llm.latency() for _ in range(300)]
    assert max(draws) > 1.5
    assert sorted(draws)[150] < 0.5
