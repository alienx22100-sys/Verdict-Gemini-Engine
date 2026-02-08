"""
Simple in-memory rate limiter for Decision Authority.
Prevents API quota abuse without external dependencies.
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Tuple

# ─────────────────────────────────────────────────────────────
# RATE LIMITER CONFIGURATION
# ─────────────────────────────────────────────────────────────

# Maximum requests per window
DEFAULT_MAX_REQUESTS = 10

# Time window in seconds (1 minute)
DEFAULT_WINDOW_SECONDS = 60


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.
    Thread-safe for concurrent requests.
    
    Usage:
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        allowed, retry_after = limiter.check("192.168.1.1")
        if not allowed:
            return {"error": f"Rate limited. Retry after {retry_after}s"}
    """
    
    def __init__(
        self, 
        max_requests: int = DEFAULT_MAX_REQUESTS, 
        window_seconds: int = DEFAULT_WINDOW_SECONDS
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = defaultdict(list)  # IP -> list of timestamps
        self._lock = Lock()
    
    def check(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for the given identifier (usually IP).
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
            If allowed, retry_after is 0.
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        with self._lock:
            # Clean old requests outside the window
            self._requests[identifier] = [
                ts for ts in self._requests[identifier] 
                if ts > window_start
            ]
            
            # Check if under limit
            if len(self._requests[identifier]) < self.max_requests:
                self._requests[identifier].append(now)
                return True, 0
            
            # Calculate retry time (when oldest request expires)
            oldest = min(self._requests[identifier])
            retry_after = int(oldest + self.window_seconds - now) + 1
            
            return False, max(1, retry_after)
    
    def cleanup(self):
        """Remove stale entries to prevent memory growth."""
        now = time.time()
        window_start = now - self.window_seconds
        
        with self._lock:
            stale_keys = [
                key for key, timestamps in self._requests.items()
                if not timestamps or max(timestamps) < window_start
            ]
            for key in stale_keys:
                del self._requests[key]


# ─────────────────────────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────────────────────────

# Global rate limiter for /api/decide endpoint
# 10 requests per minute is reasonable for hackathon demo
api_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
