from __future__ import annotations

import pytest

from app.resilience.rate_limiter import RateLimitConfig, TokenBucketRateLimiter
from tests.test_resilience.fakes import FakeAsyncRedis


@pytest.mark.asyncio
async def test_rate_limiter_blocks_when_tokens_exhausted_and_refills_over_time():
    redis = FakeAsyncRedis()
    now = 1000.0

    def time_fn() -> float:
        return now

    async def sleep_fn(_: float) -> None:
        # Don't actually sleep in unit tests.
        return None

    rl = TokenBucketRateLimiter(
        redis,  # type: ignore[arg-type]
        limits={"ddg": RateLimitConfig(tokens_per_second=1.0, capacity=2.0)},
        time_fn=time_fn,
        sleep_fn=sleep_fn,
    )

    assert await rl.acquire("ddg", timeout=0.0) is True
    assert await rl.acquire("ddg", timeout=0.0) is True
    assert await rl.acquire("ddg", timeout=0.0) is False

    now += 1.0
    assert await rl.acquire("ddg", timeout=0.0) is True


@pytest.mark.asyncio
async def test_rate_limiter_acquire_times_out_when_no_refill_occurs():
    redis = FakeAsyncRedis()
    now = 2000.0

    def time_fn() -> float:
        return now

    async def sleep_fn(dt: float) -> None:
        nonlocal now
        now += float(dt)

    rl = TokenBucketRateLimiter(
        redis,  # type: ignore[arg-type]
        limits={"reddit": RateLimitConfig(tokens_per_second=0.0, capacity=0.0)},
        time_fn=time_fn,
        sleep_fn=sleep_fn,
    )

    assert await rl.acquire("reddit", timeout=0.01) is False

