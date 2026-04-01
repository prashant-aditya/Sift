from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Callable, Mapping

from redis.asyncio import Redis


@dataclass(frozen=True)
class RateLimitConfig:
    # tokens_per_second: refill rate; capacity: burst size
    tokens_per_second: float
    capacity: float


DEFAULT_SOURCE_LIMITS: dict[str, RateLimitConfig] = {
    # Per README/blueprint
    "duckduckgo": RateLimitConfig(tokens_per_second=1.0, capacity=5.0),
    "ddg": RateLimitConfig(tokens_per_second=1.0, capacity=5.0),
    "reddit": RateLimitConfig(tokens_per_second=0.5, capacity=3.0),
    "hackernews": RateLimitConfig(tokens_per_second=2.0, capacity=10.0),
    "hn": RateLimitConfig(tokens_per_second=2.0, capacity=10.0),
    "arxiv": RateLimitConfig(tokens_per_second=1.0 / 3.0, capacity=3.0),
    "wikipedia": RateLimitConfig(tokens_per_second=5.0, capacity=20.0),
}


_ACQUIRE_LUA = r"""
-- Token-bucket: refill + consume atomically
-- KEYS[1] = tokens key
-- KEYS[2] = last_refill key
-- ARGV[1] = now (seconds, float)
-- ARGV[2] = rate (tokens/sec, float)
-- ARGV[3] = capacity (float)
-- ARGV[4] = cost (float, typically 1.0)
-- ARGV[5] = ttl_seconds (int)

local tokens_key = KEYS[1]
local last_key = KEYS[2]

local now = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local capacity = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local tokens = tonumber(redis.call("GET", tokens_key))
if tokens == nil then tokens = capacity end

local last = tonumber(redis.call("GET", last_key))
if last == nil then last = now end

local elapsed = now - last
if elapsed < 0 then elapsed = 0 end

local refill = elapsed * rate
tokens = math.min(capacity, tokens + refill)

local acquired = 0
local remaining = tokens
if tokens >= cost then
  tokens = tokens - cost
  acquired = 1
  remaining = tokens
end

redis.call("SET", tokens_key, tostring(tokens))
redis.call("SET", last_key, tostring(now))
redis.call("EXPIRE", tokens_key, ttl)
redis.call("EXPIRE", last_key, ttl)

return {acquired, remaining}
"""


class TokenBucketRateLimiter:
    """Per-source Redis-backed token bucket rate limiter."""

    def __init__(
        self,
        redis: Redis,
        *,
        limits: Mapping[str, RateLimitConfig] | None = None,
        key_prefix: str = "sift",
        time_fn: Callable[[], float] = time.time,
        sleep_fn: Callable[[float], "asyncio.Future[None]"] | None = None,
    ) -> None:
        self.redis = redis
        self._limits = dict(limits or DEFAULT_SOURCE_LIMITS)
        self._prefix = key_prefix.strip(":")
        self._now = time_fn
        self._sleep = sleep_fn or asyncio.sleep

    def _k(self, source: str, suffix: str) -> str:
        s = source.strip().lower()
        return f"{self._prefix}:rl:{s}:{suffix}"

    def _limit_for(self, source: str) -> RateLimitConfig:
        s = source.strip().lower()
        if s in self._limits:
            return self._limits[s]
        # Default: conservative 1 req/sec burst 1 if unknown.
        return RateLimitConfig(tokens_per_second=1.0, capacity=1.0)

    async def _try_acquire_once(self, source: str, *, cost: float = 1.0) -> bool:
        lim = self._limit_for(source)
        tokens_key = self._k(source, "tokens")
        last_key = self._k(source, "last_refill")
        now = float(self._now())
        ttl = int(max(60, (lim.capacity / max(lim.tokens_per_second, 1e-9)) * 5))

        res = await self.redis.eval(
            _ACQUIRE_LUA,
            numkeys=2,
            keys=[tokens_key, last_key],
            args=[now, float(lim.tokens_per_second), float(lim.capacity), float(cost), ttl],
        )
        # redis-py returns a list of ints/strings; tolerate both.
        acquired = int(res[0]) == 1  # type: ignore[index]
        return acquired

    async def acquire(self, source: str, *, timeout: float = 10.0, cost: float = 1.0) -> bool:
        """Acquire one token (cost) for a given source within timeout."""
        deadline = self._now() + float(timeout)
        while True:
            if await self._try_acquire_once(source, cost=cost):
                return True
            if self._now() >= deadline:
                return False
            # Short polling interval; Redis state is shared across workers.
            await self._sleep(0.05)

