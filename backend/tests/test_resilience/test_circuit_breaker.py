from __future__ import annotations

import pytest

from app.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from tests.test_resilience.fakes import FakeAsyncRedis


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold_failures_within_window():
    redis = FakeAsyncRedis()
    now = 1000.0

    def time_fn() -> float:
        return now

    cb = CircuitBreaker(
        "duckduckgo",
        redis,  # type: ignore[arg-type]
        failure_threshold=3,
        failure_window=60,
        cooldown=30,
        time_fn=time_fn,
    )

    for _ in range(2):
        with pytest.raises(RuntimeError):
            async with cb:
                raise RuntimeError("boom")

    # 3rd failure should open circuit.
    with pytest.raises(RuntimeError):
        async with cb:
            raise RuntimeError("boom")

    with pytest.raises(CircuitOpenError):
        async with cb:
            pass


@pytest.mark.asyncio
async def test_circuit_breaker_transitions_to_half_open_after_cooldown_and_closes_on_success():
    redis = FakeAsyncRedis()
    now = 2000.0

    def time_fn() -> float:
        return now

    cb = CircuitBreaker(
        "wikipedia",
        redis,  # type: ignore[arg-type]
        failure_threshold=2,
        failure_window=60,
        cooldown=30,
        time_fn=time_fn,
    )

    for _ in range(2):
        with pytest.raises(RuntimeError):
            async with cb:
                raise RuntimeError("boom")

    with pytest.raises(CircuitOpenError):
        async with cb:
            pass

    # After cooldown, allow half-open attempt.
    now += 31.0
    async with cb:
        pass

    # Subsequent enters should be allowed (closed).
    async with cb:
        pass


@pytest.mark.asyncio
async def test_circuit_breaker_failure_in_half_open_reopens_immediately():
    redis = FakeAsyncRedis()
    now = 3000.0

    def time_fn() -> float:
        return now

    cb = CircuitBreaker(
        "hackernews",
        redis,  # type: ignore[arg-type]
        failure_threshold=2,
        failure_window=60,
        cooldown=30,
        time_fn=time_fn,
    )

    for _ in range(2):
        with pytest.raises(RuntimeError):
            async with cb:
                raise RuntimeError("boom")

    now += 31.0
    with pytest.raises(RuntimeError):
        async with cb:
            raise RuntimeError("still down")

    with pytest.raises(CircuitOpenError):
        async with cb:
            pass

