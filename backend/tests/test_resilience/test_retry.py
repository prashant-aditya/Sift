from __future__ import annotations

import pytest

from app.resilience.retry import RetryError, with_retry


@pytest.mark.asyncio
async def test_retry_backoff_timing_with_jitter_is_applied_and_then_succeeds():
    sleeps: list[float] = []

    async def sleep_fn(dt: float) -> None:
        sleeps.append(dt)

    # No randomness in test: always midpoint.
    def random_fn(a: float, b: float) -> float:  # noqa: ARG001
        return 1.0

    calls = {"n": 0}

    @with_retry(max_retries=2, backoff_base=1.0, sleep_fn=sleep_fn, random_fn=random_fn)
    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("nope")
        return "ok"

    assert await flaky() == "ok"
    assert sleeps == [1.0, 2.0]


@pytest.mark.asyncio
async def test_retry_gives_up_after_max_retries():
    async def sleep_fn(_: float) -> None:
        return None

    @with_retry(max_retries=1, backoff_base=1.0, sleep_fn=sleep_fn)
    async def always_fail() -> str:
        raise TimeoutError("nope")

    with pytest.raises(RetryError):
        await always_fail()

