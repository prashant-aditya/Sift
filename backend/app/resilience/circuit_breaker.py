from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

from redis.asyncio import Redis


class CircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is open for a source."""

    def __init__(self, source_name: str, retry_after_seconds: int) -> None:
        self.source_name = source_name
        self.retry_after_seconds = int(max(0, retry_after_seconds))
        super().__init__(
            f"circuit_open source={source_name} retry_after={self.retry_after_seconds}s"
        )


@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 5
    failure_window_seconds: int = 60
    cooldown_seconds: int = 30
    key_prefix: str = "sift"


class CircuitBreaker:
    """Per-source circuit breaker with Redis-backed state.

    State machine:
      CLOSED -> OPEN -> HALF_OPEN -> CLOSED

    Redis keys:
      cb:{source}:state      -> "closed" | "open" | "half_open"
      cb:{source}:failures   -> int (failure count in window)
      cb:{source}:last_fail  -> unix timestamp seconds (float stored as string)
      cb:{source}:opened_at  -> unix timestamp seconds (float stored as string)
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(
        self,
        source_name: str,
        redis: Redis,
        *,
        config: CircuitBreakerConfig | None = None,
        failure_threshold: int | None = None,
        failure_window: int | None = None,
        cooldown: int | None = None,
        key_prefix: str | None = None,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.source_name = source_name.strip().lower()
        self.redis = redis
        cfg = config or CircuitBreakerConfig()
        self.failure_threshold = int(
            failure_threshold
            if failure_threshold is not None
            else cfg.failure_threshold
        )
        self.failure_window_seconds = int(
            failure_window if failure_window is not None else cfg.failure_window_seconds
        )
        self.cooldown_seconds = int(
            cooldown if cooldown is not None else cfg.cooldown_seconds
        )
        self._prefix = (key_prefix if key_prefix is not None else cfg.key_prefix).strip(
            ":"
        )
        self._now = time_fn

    @property
    def _base(self) -> str:
        return f"{self._prefix}:cb:{self.source_name}"

    def _k(self, suffix: str) -> str:
        return f"{self._base}:{suffix}"

    async def __aenter__(self) -> "CircuitBreaker":
        state = await self._get_state()
        if state == self.STATE_OPEN:
            retry_after = await self._retry_after_seconds()
            if retry_after <= 0:
                await self._set_state(self.STATE_HALF_OPEN)
            else:
                raise CircuitOpenError(self.source_name, retry_after)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[override]
        if exc_type is None:
            await self._record_success()
        else:
            await self._record_failure()

    async def _get_state(self) -> str:
        raw = await self.redis.get(self._k("state"))
        state = (raw or self.STATE_CLOSED).strip().lower()
        if state not in {self.STATE_CLOSED, self.STATE_OPEN, self.STATE_HALF_OPEN}:
            return self.STATE_CLOSED
        return state

    async def _set_state(self, state: str) -> None:
        await self.redis.set(self._k("state"), state)

    async def _get_float(self, key: str) -> Optional[float]:
        raw = await self.redis.get(key)
        if raw is None:
            return None
        try:
            return float(raw)
        except Exception:
            return None

    async def _get_int(self, key: str) -> Optional[int]:
        raw = await self.redis.get(key)
        if raw is None:
            return None
        try:
            return int(float(raw))
        except Exception:
            return None

    async def _retry_after_seconds(self) -> int:
        opened_at = await self._get_float(self._k("opened_at"))
        if opened_at is None:
            return 0
        remaining = (opened_at + float(self.cooldown_seconds)) - self._now()
        return int(remaining) if remaining > 0 else 0

    async def _record_failure(self) -> None:
        now = self._now()
        failures_key = self._k("failures")
        last_fail_key = self._k("last_fail")
        opened_at_key = self._k("opened_at")
        state_key = self._k("state")

        # Use a small transaction to avoid interleaving updates across workers.
        async with self.redis.pipeline(transaction=True) as pipe:
            last_fail_raw, state_raw, failures_raw = (
                await pipe.get(last_fail_key).get(state_key).get(failures_key).execute()
            )

        try:
            last_fail = float(last_fail_raw) if last_fail_raw is not None else None
        except Exception:
            last_fail = None
        try:
            failures = int(float(failures_raw)) if failures_raw is not None else 0
        except Exception:
            failures = 0

        # Reset the rolling window if last failure was too old.
        if last_fail is None or (now - last_fail) > float(self.failure_window_seconds):
            failures = 1
        else:
            failures += 1

        new_state = (state_raw or self.STATE_CLOSED).strip().lower()
        if new_state == self.STATE_HALF_OPEN:
            # Any failure in HALF_OPEN trips immediately back to OPEN.
            failures = max(failures, self.failure_threshold)

        should_open = failures >= self.failure_threshold

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(failures_key, str(int(failures)))
            pipe.set(last_fail_key, str(float(now)))
            if should_open:
                pipe.set(state_key, self.STATE_OPEN)
                pipe.set(opened_at_key, str(float(now)))
            # Expire housekeeping keys so Redis doesn't grow unbounded.
            ttl = max(self.failure_window_seconds, self.cooldown_seconds) + 120
            pipe.expire(failures_key, ttl)
            pipe.expire(last_fail_key, ttl)
            pipe.expire(state_key, ttl)
            pipe.expire(opened_at_key, ttl)
            await pipe.execute()

    async def _record_success(self) -> None:
        state = await self._get_state()
        if state in {self.STATE_HALF_OPEN, self.STATE_OPEN}:
            # Success in HALF_OPEN closes the breaker; success while OPEN is treated as recovery.
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.set(self._k("state"), self.STATE_CLOSED)
                pipe.set(self._k("failures"), "0")
                pipe.delete(self._k("opened_at"))
                pipe.delete(self._k("last_fail"))
                ttl = max(self.failure_window_seconds, self.cooldown_seconds) + 120
                pipe.expire(self._k("state"), ttl)
                pipe.expire(self._k("failures"), ttl)
                await pipe.execute()
            return

        # CLOSED: keep it closed and reset failures for good measure.
        await self.redis.set(self._k("failures"), "0")
