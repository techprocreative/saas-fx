"""
Security Middleware for Rate Limiting and Input Validation
Implements Phase 1.1 of Production Roadmap
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from typing import Callable
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute", "2000/hour"],
    storage_uri="memory://",  # Use Redis in production
    headers_enabled=True
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize incoming requests"""
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bOR\b.*=.*)",
        r"('|(\\'))",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.",
        r"%2e%2e",
        r"\.\.\\",
    ]
    
    def __init__(self, app):
        super().__init__(app)
        self.sql_pattern = re.compile("|".join(self.SQL_INJECTION_PATTERNS), re.IGNORECASE)
        self.xss_pattern = re.compile("|".join(self.XSS_PATTERNS), re.IGNORECASE)
        self.path_pattern = re.compile("|".join(self.PATH_TRAVERSAL_PATTERNS), re.IGNORECASE)
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check request size (prevent DOS)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            logger.warning(f"Request too large from {request.client.host}: {content_length} bytes")
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"error": "Request too large"}
            )
        
        # Validate URL path
        if self.path_pattern.search(str(request.url.path)):
            logger.warning(f"Path traversal attempt from {request.client.host}: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid request path"}
            )
        
        # Validate query parameters
        for key, value in request.query_params.items():
            if self._is_malicious(value):
                logger.warning(f"Malicious query parameter from {request.client.host}: {key}={value}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Invalid query parameter"}
                )
        
        # Log request for audit trail
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host} at {datetime.utcnow().isoformat()}"
        )
        
        response = await call_next(request)
        return response
    
    def _is_malicious(self, value: str) -> bool:
        """Check if value contains malicious patterns"""
        if self.sql_pattern.search(value):
            return True
        if self.xss_pattern.search(value):
            return True
        return False


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Optional: Whitelist specific IPs for admin endpoints"""
    
    def __init__(self, app, whitelisted_ips: list = None, protected_paths: list = None):
        super().__init__(app)
        self.whitelisted_ips = whitelisted_ips or []
        self.protected_paths = protected_paths or ["/admin", "/internal"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check if path is protected
        is_protected = any(request.url.path.startswith(path) for path in self.protected_paths)
        
        if is_protected and self.whitelisted_ips:
            client_ip = request.client.host
            if client_ip not in self.whitelisted_ips:
                logger.warning(f"Unauthorized access attempt from {client_ip} to {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "Access forbidden"}
                )
        
        response = await call_next(request)
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID for tracing"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        import uuid
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


def setup_security_middleware(app):
    """Setup all security middleware for the application"""
    
    # Add request ID for tracing
    app.add_middleware(RequestIDMiddleware)
    
    # Add security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add request validation
    app.add_middleware(RequestValidationMiddleware)
    
    # Optional: Add IP whitelist for admin endpoints
    # app.add_middleware(
    #     IPWhitelistMiddleware,
    #     whitelisted_ips=["127.0.0.1", "::1"],
    #     protected_paths=["/admin", "/internal"]
    # )
    
    # Add rate limiting handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    logger.info("Security middleware initialized successfully")


# Rate limiting decorators for specific endpoints
def rate_limit_auth(func):
    """Stricter rate limiting for authentication endpoints"""
    return limiter.limit("5/minute")(func)


def rate_limit_api(func):
    """Standard rate limiting for API endpoints"""
    return limiter.limit("100/minute")(func)


def rate_limit_websocket(func):
    """Rate limiting for WebSocket connections"""
    return limiter.limit("10/minute")(func)
