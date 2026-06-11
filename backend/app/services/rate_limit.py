import time
from collections import defaultdict

from fastapi import HTTPException, status


class SlidingWindowRateLimiter:
    """In-memory sliding-window rate limiter keyed by an arbitrary string
    (e.g. client IP or username).

    Single-process only — fine for this app's target deployment (one
    uvicorn worker on a small self-hosted box). Opportunistically prunes
    stale keys so the dict doesn't grow unboundedly.
    """

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, detail: str) -> None:
        now = time.monotonic()

        if len(self._attempts) > 1000:
            for k in list(self._attempts):
                if all(now - t >= self.window_seconds for t in self._attempts[k]):
                    del self._attempts[k]

        attempts = [t for t in self._attempts[key] if now - t < self.window_seconds]
        if len(attempts) >= self.max_attempts:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)
        attempts.append(now)
        self._attempts[key] = attempts

    def reset(self) -> None:
        self._attempts.clear()
