from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import HTTPException, status


class SlidingWindowLimiter:
    def __init__(self, attempts: int = 5, window_minutes: int = 5) -> None:
        self.attempts = attempts
        self.window = timedelta(minutes=window_minutes)
        self.events: dict[str, deque[datetime]] = defaultdict(deque)
        self.lock = Lock()

    def check(self, key: str) -> None:
        now = datetime.now(UTC)
        cutoff = now - self.window
        with self.lock:
            events = self.events[key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= self.attempts:
                retry_after = max(1, int((events[0] + self.window - now).total_seconds()))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Demasiados intentos. Inténtalo nuevamente en unos minutos.",
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)

    def reset(self, key: str) -> None:
        with self.lock:
            self.events.pop(key, None)


login_limiter = SlidingWindowLimiter()
