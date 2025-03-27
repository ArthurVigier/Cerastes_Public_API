"""
Rate limiting middleware.
Protects the API against abuse by limiting the number of requests per IP or API key.
"""

import time
import logging
from typing import Dict, Optional, List, Callable, Tuple
from collections import defaultdict
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Logging configuration
logger = logging.getLogger("rate_limit_middleware")

class RateLimiter:
    """Rate limiter manager based on a sliding window algorithm."""
    
    def __init__(self, window_size: int = 60, max_requests: int = 100):
        """
        Initializes the rate limiter.
        
        Args:
            window_size: Window size in seconds
            max_requests: Maximum number of requests allowed in the window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        # Structure: {identifier: [(timestamp1, 1), (timestamp2, 1), ...]}
        self.request_records = defaultdict(list)
    
    def is_rate_limited(self, identifier: str) -> Tuple[bool, int, int]:
        """
        Checks if the identifier has exceeded its request limit.
        
        Args:
            identifier: Unique identifier (IP or API key)
            
        Returns:
            (is_limited, remaining_requests, wait_time_in_seconds)
        """
        now = time.time()
        records = self.request_records[identifier]
        
        # Remove records that are too old
        cutoff = now - self.window_size
        records = [(ts, count) for ts, count in records if ts > cutoff]
        self.request_records[identifier] = records
        
        # Calculate the total number of requests in the window
        total_requests = sum(count for _, count in records)
        
        # Check if the limit is reached
        if total_requests >= self.max_requests:
            # Calculate the wait time
            if records:
                oldest = records[0][0]
                wait_time = int(self.window_size - (now - oldest)) + 1
                return True, 0, wait_time
            return True, 0, self.window_size
        
        # Add this request
        records.append((now, 1))
        self.request_records[identifier] = records
        
        # Return the number of remaining requests
        remaining = self.max_requests - total_requests - 1
        return False, remaining, 0

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request rate."""
    
    def __init__(
        self,
        app: ASGIApp,
        global_rate_limit: int = 1000,
        ip_rate_limit: int = 100,
        api_key_rate_limit: int = 200,
        window_size: int = 60,
        exclude_paths: List[str] = None,
        exclude_prefixes: List[str] = None,
    ):
        """
        Initializes the rate limiting middleware.
        
        Args:
            app: ASGI Application
            global_rate_limit: Global limit of requests per minute
            ip_rate_limit: Limit of requests per IP per minute
            api_key_rate_limit: Limit of requests per API key per minute
            window_size: Window size in seconds
            exclude_paths: Paths excluded from rate limiting
            exclude_prefixes: Path prefixes excluded from rate limiting
        """
        super().__init__(app)
        self.global_limiter = RateLimiter(window_size, global_rate_limit)
        self.ip_limiter = RateLimiter(window_size, ip_rate_limit)
        self.api_key_limiter = RateLimiter(window_size, api_key_rate_limit)
        self.exclude_paths = exclude_paths or ["/api/health", "/api/docs", "/api/redoc", "/api/openapi.json"]
        self.exclude_prefixes = exclude_prefixes or ["/static/", "/docs/"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Processes requests with rate limiting."""
        # Check if this path is excluded
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Check global limits
        global_limited, global_remaining, global_wait = self.global_limiter.is_rate_limited("global")
        if global_limited:
            return self._create_rate_limit_response(global_wait, 0, "global")
        
        # Get the request identifier (IP or API key)
        client_ip = request.client.host if request.client else "unknown"
        api_key = request.headers.get("X-API-Key")
        
        # Check IP-based limits
        ip_limited, ip_remaining, ip_wait = self.ip_limiter.is_rate_limited(client_ip)
        if ip_limited:
            return self._create_rate_limit_response(ip_wait, 0, "ip", client_ip)
        
        # Check API key-based limits
        if api_key:
            key_limited, key_remaining, key_wait = self.api_key_limiter.is_rate_limited(api_key)
            if key_limited:
                return self._create_rate_limit_response(key_wait, 0, "api_key")
            
            # Add the number of remaining requests to the response header
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(key_remaining)
            response.headers["X-RateLimit-Limit"] = str(self.api_key_limiter.max_requests)
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.api_key_limiter.window_size)
            return response
        
        # Add the number of remaining requests to the response header (based on IP)
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(ip_remaining)
        response.headers["X-RateLimit-Limit"] = str(self.ip_limiter.max_requests)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.ip_limiter.window_size)
        return response
    
    def _is_excluded_path(self, path: str) -> bool:
        """Checks if the path is excluded from rate limiting."""
        if path in self.exclude_paths:
            return True
        
        for prefix in self.exclude_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _create_rate_limit_response(self, wait_time: int, remaining: int, limiter_type: str, identifier: str = None) -> Response:
        """Creates a response for a rate-limited request."""
        detail = f"Rate limit exceeded. Please try again in {wait_time} seconds."
        if identifier and limiter_type == "ip":
            logger.warning(f"Rate limit exceeded for IP {identifier}")
            
        return JSONResponse(
            status_code=429,
            content={
                "detail": detail,
                "type": "rate_limit_exceeded",
                "limiter": limiter_type
            },
            headers={
                "Retry-After": str(wait_time),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + wait_time)
            }
        )