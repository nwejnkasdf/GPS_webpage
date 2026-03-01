import asyncio
import time


class RateLimiter:
    """Token bucket rate limiter for async usage."""

    def __init__(self, rate: int = 1, period: float = 2.0):
        self._rate = rate
        self._period = period
        self._semaphore = asyncio.Semaphore(rate)
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._semaphore:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_call
                wait = self._period / self._rate - elapsed
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last_call = time.monotonic()


# Global singleton limiters
boj_limiter = RateLimiter(rate=1, period=2.5)     # 1 req per 2.5s
solved_limiter = RateLimiter(rate=3, period=1.0)  # 3 req per 1s
