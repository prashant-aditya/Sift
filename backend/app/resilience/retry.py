from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

try:
    from typing import ParamSpec  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    from typing_extensions import ParamSpec


class RetryError(RuntimeError):
    """Raised when an operation keeps failing beyond max retries."""

    def __init__(self, message: str, *, attempts: int) -> None:
        self.attempts = int(attempts)
        super().__init__(message)


P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int = 2
    backoff_base: float = 1.0
    jitter_ratio: float = 0.2  # +/- 20%
    retryable_exceptions: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError)


def with_retry(
    *,
    max_retries: int = 2,
    backoff_base: float = 1.0,
    jitter_ratio: float = 0.2,
    retryable_exceptions: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError),
    sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
    random_fn: Callable[[float, float], float] = random.uniform,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Exponential backoff retry decorator for async callables.

    Delay: backoff_base * 2^attempt (1s, 2s, 4s...)
    Jitter: +/- jitter_ratio (default 20%) to avoid thundering herd.
    """

    cfg = RetryConfig(
        max_retries=int(max_retries),
        backoff_base=float(backoff_base),
        jitter_ratio=float(jitter_ratio),
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            attempts = 0
            while True:
                try:
                    return await fn(*args, **kwargs)
                except cfg.retryable_exceptions as exc:
                    if attempts >= cfg.max_retries:
                        raise RetryError(
                            f"retry_exhausted after {attempts + 1} attempts: {exc}",
                            attempts=attempts + 1,
                        ) from exc

                    base_delay = cfg.backoff_base * (2**attempts)
                    jitter_low = max(0.0, 1.0 - cfg.jitter_ratio)
                    jitter_high = 1.0 + cfg.jitter_ratio
                    delay = base_delay * float(random_fn(jitter_low, jitter_high))
                    attempts += 1
                    await sleep_fn(delay)
                except BaseException:
                    # Non-retryable exceptions propagate immediately.
                    raise

        return wrapped

    return decorator

