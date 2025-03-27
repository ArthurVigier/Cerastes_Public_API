import re
import logging
import secrets
from typing import Dict, List, Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Logging configuration
logger = logging.getLogger("security_middleware")

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware implementing various security protections."""
    
    def __init__(
        self,
        app: ASGIApp,
        enable_xss_protection: bool = True,
        enable_hsts: bool = True,
        enable_content_type_options: bool = True,
        enable_frame_options: bool = True,
        enable_referrer_policy: bool = True,
        enable_csp: bool = True,
        enable_cors_protection: bool = True,
        csp_directives: Optional[Dict[str, str]] = None,
        allowed_origins: List[str] = None,
        allowed_methods: List[str] = None,
    ):
        """
        Initializes the security middleware.
        
        Args:
            app: ASGI Application
            enable_xss_protection: Enable XSS protection
            enable_hsts: Enable HSTS (HTTP Strict Transport Security)
            enable_content_type_options: Enable X-Content-Type-Options
            enable_frame_options: Enable X-Frame-Options
            enable_referrer_policy: Enable Referrer-Policy
            enable_csp: Enable Content-Security-Policy
            enable_cors_protection: Enable advanced CORS protection
            csp_directives: Custom CSP directives
            allowed_origins: Allowed origins for CORS
            allowed_methods: Allowed HTTP methods for CORS
        """
        super().__init__(app)
        self.enable_xss_protection = enable_xss_protection
        self.enable_hsts = enable_hsts
        self.enable_content_type_options = enable_content_type_options
        self.enable_frame_options = enable_frame_options
        self.enable_referrer_policy = enable_referrer_policy
        self.enable_csp = enable_csp
        self.enable_cors_protection = enable_cors_protection
        
        # CSP parameters
        self.csp_directives = csp_directives or {
            "default-src": "'self'",
            "script-src": "'self'",
            "style-src": "'self'",
            "img-src": "'self' data:",
            "font-src": "'self'",
            "connect-src": "'self'",
            "frame-ancestors": "'none'",
            "form-action": "'self'",
            "base-uri": "'self'",
            "object-src": "'none'"
        }
        
        # CORS parameters
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        
        # Generate a nonce for CSP (could be regenerated for each request)
        self.csp_nonce = secrets.token_urlsafe(16)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Adds security headers to the response."""
        # Check origin for advanced CORS protection
        if self.enable_cors_protection and request.method != "OPTIONS":
            origin = request.headers.get("Origin")
            if origin and not self._is_origin_allowed(origin):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origin not allowed"}
                )
        
        # Process the request normally
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response, request)
        
        return response
    
    def _add_security_headers(self, response: Response, request: Request) -> None:
        """Adds security headers to the response."""
        # X-XSS-Protection
        if self.enable_xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict-Transport-Security (HSTS)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # X-Content-Type-Options
        if self.enable_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        if self.enable_frame_options:
            response.headers["X-Frame-Options"] = "DENY"
        
        # Referrer-Policy
        if self.enable_referrer_policy:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content-Security-Policy
        if self.enable_csp and not self._is_api_endpoint(request.url.path):
            # Generate CSP policy
            csp_parts = []
            for directive, value in self.csp_directives.items():
                # Add nonce for script-src and style-src directives
                if directive in ["script-src", "style-src"] and "'unsafe-inline'" not in value:
                    value = f"{value} 'nonce-{self.csp_nonce}'"
                csp_parts.append(f"{directive} {value}")
            
            response.headers["Content-Security-Policy"] = "; ".join(csp_parts)
            # Add nonce to response context for use in templates
            request.state.csp_nonce = self.csp_nonce
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Checks if the origin is allowed."""
        if "*" in self.allowed_origins:
            return True
        
        return origin in self.allowed_origins or self._matches_wildcard_origin(origin)
    
    def _matches_wildcard_origin(self, origin: str) -> bool:
        """Checks if the origin matches a wildcard pattern."""
        for allowed_origin in self.allowed_origins:
            if allowed_origin.startswith("*."):
                pattern = allowed_origin.replace("*.", ".*\\.")
                if re.match(pattern, origin):
                    return True
        return False
    
    def _is_api_endpoint(self, path: str) -> bool:
        """Checks if the path is an API endpoint (to avoid CSP on JSON APIs)."""
        return path.startswith("/api/") or path.startswith("/auth/")