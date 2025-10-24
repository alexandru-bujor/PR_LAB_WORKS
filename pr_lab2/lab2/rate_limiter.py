import time
from collections import deque, defaultdict
from threading import Lock

class RateLimiter:
    def __init__(self, max_per_sec:int = 5):
        self.max_per_sec = max_per_sec
        self._buckets = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key:str) -> bool:
        now = time.time()
        with self._lock:
            dq = self._buckets[key]
            cutoff = now - 1.0
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) < self.max_per_sec:
                dq.append(now)
                return True
            return False
