import time
import hashlib
import json
import logging
from typing import Dict, Any, Optional, List, Callable, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse, Response as FastAPIResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Logging configuration
logger = logging.getLogger("cache_middleware")

class CacheEntry:
    """Cache entry with expiration."""
    
    def __init__(self, response: bytes, headers: Dict[str, str], status_code: int, ttl: int):
        """
        Initializes a cache entry.
        
        Args:
            response: Response body in bytes
            headers: Response headers
            status_code: HTTP status code
            ttl: Time to live in seconds
        """
        self.response = response
        self.headers = headers
        self.status_code = status_code
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl
    
    def is_expired(self) -> bool:
        """Checks if the cache entry has expired."""
        return time.time() > self.expires_at
    
    def get_age(self) -> int:
        """Returns the age of the entry in seconds."""
        return int(time.time() - self.created_at)

class ResponseCache:
    """HTTP response cache manager."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initializes the cache.
        
        Args:
            max_size: Maximum cache size (number of entries)
            default_ttl: Default time to live for entries in seconds
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """
        Retrieves a cache entry by its key.
        
        Args:
            key: Entry key
            
        Returns:
            The cache entry or None if not found or expired
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            return None
        
        return entry
    
    def set(self, key: str, response: bytes, headers: Dict[str, str], status_code: int, ttl: Optional[int] = None) -> None:
        """
        Adds an entry to the cache.
        
        Args:
            key: Entry key
            response: Response body in bytes
            headers: Response headers
            status_code: HTTP status code
            ttl: Time to live in seconds (uses default value if None)
        """
        # Remove expired entries
        self._clean_expired()
        
        # Ensure the cache doesn't exceed its maximum size
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        # Add the new entry
        ttl = ttl if ttl is not None else self.default_ttl
        self.cache[key] = CacheEntry(response, headers, status_code, ttl)
    
    def invalidate(self, key_prefix: str) -> int:
        """
        Invalidates cache entries starting with a prefix.
        
        Args:
            key_prefix: Prefix of keys to invalidate
            
        Returns:
            Number of invalidated entries
        """
        keys_to_delete = [k for k in self.cache.keys() if k.startswith(key_prefix)]
        for key in keys_to_delete:
            del self.cache[key]
        return len(keys_to_delete)
    
    def _clean_expired(self) -> int:
        """Removes expired entries from the cache."""
        keys_to_delete = [k for k, v in self.cache.items() if v.is_expired()]
        for key in keys_to_delete:
            del self.cache[key]
        return len(keys_to_delete)
    
    def _evict_oldest(self) -> None:
        """Removes the oldest entry from the cache."""
        if not self.cache:
            return
        
        # Find the oldest entry
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
        del self.cache[oldest_key]

class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for caching responses."""
    
    def __init__(
        self,
        app: ASGIApp,
        ttl: int = 300,
        max_size: int = 1000,
        include_paths: List[str] = None,
        include_prefixes: List[str] = None,
        exclude_paths: List[str] = None,
        exclude_prefixes: List[str] = None,
        cache_query_params: bool = True,
        cache_by_api_key: bool = True
    ):
        """
        Initializes the cache middleware.
        
        Args:
            app: ASGI Application
            ttl: Time to live for entries in seconds
            max_size: Maximum cache size
            include_paths: Paths to include in the cache
            include_prefixes: Path prefixes to include in the cache
            exclude_paths: Paths to exclude from the cache
            exclude_prefixes: Path prefixes to exclude from the cache
            cache_query_params: Whether query parameters should be included in the cache key
            cache_by_api_key: Whether caching should be differentiated by API key
        """
        super().__init__(app)
        self.cache = ResponseCache(max_size, ttl)
        self.include_paths = include_paths or ["/api/health"]
        self.include_prefixes = include_prefixes or ["/api/inference/", "/api/transcription/"]
        self.exclude_paths = exclude_paths or ["/api/tasks/"]
        self.exclude_prefixes = exclude_prefixes or ["/auth/", "/api/upload/"]
        self.cache_query_params = cache_query_params
        self.cache_by_api_key = cache_by_api_key
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Processes requests with caching."""
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Check if the path should be cached
        if not self._should_cache_path(request.url.path):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Check if the response is in the cache
        cache_entry = self.cache.get(cache_key)
        if cache_entry:
            # Add cache-specific headers
            headers = dict(cache_entry.headers)
            headers["X-Cache"] = "HIT"
            headers["Age"] = str(cache_entry.get_age())
            
            # Create response with cached data
            return Response(
                content=cache_entry.response,
                status_code=cache_entry.status_code,
                headers=headers
            )
        
        # Get response from the application
        response = await call_next(request)
        
        # Only cache successful responses
        if 200 <= response.status_code < 300:
            # Get headers and body of the response
            headers = dict(response.headers)
            headers["X-Cache"] = "MISS"
            
            # Check cache headers
            cache_control = response.headers.get("Cache-Control", "")
            if "no-cache" not in cache_control and "no-store" not in cache_control:
                # Get response body
                response_body = b""
                if isinstance(response, JSONResponse):
                    response_body = json.dumps(response.body_dict).encode()
                else:
                    response_body = await self._get_response_body(response)
                
                # Determine TTL from headers or use default value
                ttl = self._get_ttl_from_headers(response.headers)
                
                # Store response in cache
                self.cache.set(cache_key, response_body, headers, response.status_code, ttl)
                
                # Add cache-specific headers to original response
                response.headers["X-Cache"] = "MISS"
        
        return response
    
    def _should_cache_path(self, path: str) -> bool:
        """Checks if the path should be cached."""
        # Check exclusions
        if path in self.exclude_paths:
            return False
        
        for prefix in self.exclude_prefixes:
            if path.startswith(prefix):
                return False
        
        # Check inclusions
        if path in self.include_paths:
            return True
        
        for prefix in self.include_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generates a unique key for the request."""
        key_parts = [request.method, request.url.path]
        
        # Add query parameters if needed
        if self.cache_query_params and request.url.query:
            key_parts.append(request.url.query)
        
        # Differentiate by API key if needed
        if self.cache_by_api_key:
            api_key = request.headers.get("X-API-Key", "anonymous")
            key_parts.append(api_key)
        
        # Generate a hash for the key
        key = ":".join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()
    
    async def _get_response_body(self, response: Response) -> bytes:
        """Retrieves the response body."""
        if hasattr(response, "body"):
            return response.body
        
        # For StreamingResponse and others
        # Note: this might not work for all responses
        try:
            return b"".join([chunk async for chunk in response.body_iterator])
        except Exception:
            # In case of error, don't cache
            return b""
    
    def _get_ttl_from_headers(self, headers: Dict[str, str]) -> Optional[int]:
        """Determines TTL from HTTP headers."""
        # Check Cache-Control: max-age header
        cache_control = headers.get("Cache-Control", "")
        for directive in cache_control.split(","):
            directive = directive.strip()
            if directive.startswith("max-age="):
                try:
                    return int(directive.split("=")[1])
                except (ValueError, IndexError):
                    pass
        
        # Check Expires header
        expires = headers.get("Expires")
        if expires:
            try:
                from email.utils import parsedate_to_datetime
                expires_time = parsedate_to_datetime(expires).timestamp()
                ttl = expires_time - time.time()
                return max(0, int(ttl))
            except Exception:
                pass
        
        # Use the cache default value
        return None