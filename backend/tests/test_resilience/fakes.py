from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class _QueuedCmd:
    name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class FakeAsyncRedis:
    """Tiny in-memory async Redis fake for unit tests."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._expiry_at: dict[str, float] = {}

    def _purge_if_expired(self, key: str) -> None:
        exp = self._expiry_at.get(key)
        if exp is not None and time.time() >= exp:
            self._values.pop(key, None)
            self._expiry_at.pop(key, None)

    async def get(self, key: str) -> Optional[str]:
        self._purge_if_expired(key)
        return self._values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._values[key] = str(value)
        if ex is not None:
            self._expiry_at[key] = time.time() + float(ex)

    async def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self._values:
                n += 1
            self._values.pop(k, None)
            self._expiry_at.pop(k, None)
        return n

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        if key not in self._values:
            return False
        self._expiry_at[key] = time.time() + float(ttl_seconds)
        return True

    @contextlib.asynccontextmanager
    async def pipeline(self, transaction: bool = True):  # noqa: ARG002
        pipe = _FakePipeline(self)
        try:
            yield pipe
        finally:
            pass

    async def eval(self, script: str, numkeys: int, keys: list[str], args: list[Any]):  # noqa: ARG002
        # Implements the specific acquire script in rate_limiter.py.
        if numkeys != 2:
            raise ValueError("fake eval supports exactly 2 keys")
        tokens_key, last_key = keys
        now = float(args[0])
        rate = float(args[1])
        cap = float(args[2])
        cost = float(args[3])
        ttl = int(float(args[4]))

        tok_raw = await self.get(tokens_key)
        tokens = float(tok_raw) if tok_raw is not None else cap
        last_raw = await self.get(last_key)
        last = float(last_raw) if last_raw is not None else now

        elapsed = max(0.0, now - last)
        tokens = min(cap, tokens + elapsed * rate)

        acquired = 0
        if tokens >= cost:
            tokens -= cost
            acquired = 1

        await self.set(tokens_key, str(tokens))
        await self.set(last_key, str(now))
        await self.expire(tokens_key, ttl)
        await self.expire(last_key, ttl)
        return [acquired, tokens]

    async def aclose(self) -> None:
        return None


class _FakePipeline:
    def __init__(self, redis: FakeAsyncRedis) -> None:
        self._redis = redis
        self._cmds: list[_QueuedCmd] = []

    def get(self, key: str):
        self._cmds.append(_QueuedCmd("get", (key,), {}))
        return self

    def set(self, key: str, value: str):
        self._cmds.append(_QueuedCmd("set", (key, value), {}))
        return self

    def delete(self, *keys: str):
        self._cmds.append(_QueuedCmd("delete", keys, {}))
        return self

    def expire(self, key: str, ttl_seconds: int):
        self._cmds.append(_QueuedCmd("expire", (key, ttl_seconds), {}))
        return self

    async def execute(self) -> list[Any]:
        out: list[Any] = []
        for cmd in self._cmds:
            fn = getattr(self._redis, cmd.name)
            out.append(await fn(*cmd.args, **cmd.kwargs))
        self._cmds.clear()
        return out

