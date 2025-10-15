"""
Global Error Handlers
Implements Phase 1.3 of Production Roadmap
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
import logging

from .logging_config import get_request_logger, audit_logger

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API Error"""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation Error"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class AuthenticationError(APIError):
    """Authentication Error"""
    def __init__(self, message: str = "Authentication failed", details: dict = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, details)


class AuthorizationError(APIError):
    """Authorization Error"""
    def __init__(self, message: str = "Insufficient permissions", details: dict = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, details)


class NotFoundError(APIError):
    """Resource Not Found Error"""
    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, details)


class ConflictError(APIError):
    """Conflict Error"""
    def __init__(self, message: str = "Resource conflict", details: dict = None):
        super().__init__(message, status.HTTP_409_CONFLICT, details)


class DatabaseError(APIError):
    """Database Error"""
    def __init__(self, message: str = "Database error", details: dict = None):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


class ExternalServiceError(APIError):
    """External Service Error"""
    def __init__(self, message: str = "External service error", details: dict = None):
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE, details)


async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors"""
    request_id = getattr(request.state, 'request_id', None)
    
    logger.error(
        f"API Error: {exc.message}",
        extra={
            'request_id': request_id,
            'status_code': exc.status_code,
            'path': request.url.path,
            'method': request.method,
            'details': exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'error': exc.message,
            'details': exc.details,
            'request_id': request_id,
            'timestamp': 'utc_now'
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    request_id = getattr(request.state, 'request_id', None)
    
    errors = []
    for error in exc.errors():
        errors.append({
            'field': '.'.join(str(x) for x in error['loc']),
            'message': error['msg'],
            'type': error['type']
        })
    
    logger.warning(
        f"Validation Error on {request.url.path}",
        extra={
            'request_id': request_id,
            'errors': errors
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            'error': 'Validation failed',
            'details': errors,
            'request_id': request_id
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    request_id = getattr(request.state, 'request_id', None)
    
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            'request_id': request_id,
            'path': request.url.path,
            'method': request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'error': exc.detail,
            'request_id': request_id
        }
    )


async def database_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    request_id = getattr(request.state, 'request_id', None)
    
    logger.error(
        f"Database Error: {str(exc)}",
        extra={
            'request_id': request_id,
            'path': request.url.path,
            'method': request.method
        },
        exc_info=True
    )
    
    # Log to audit for security
    audit_logger.log_system_event(
        event='database_error',
        component='database',
        status='error',
        details={'error': str(exc), 'request_id': request_id}
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            'error': 'Database error occurred',
            'request_id': request_id
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    request_id = getattr(request.state, 'request_id', None)
    
    logger.critical(
        f"Unhandled Exception: {str(exc)}",
        extra={
            'request_id': request_id,
            'path': request.url.path,
            'method': request.method,
            'client_host': request.client.host if request.client else 'unknown'
        },
        exc_info=True
    )
    
    # Log to audit for security monitoring
    audit_logger.log_system_event(
        event='unhandled_exception',
        component='application',
        status='critical',
        details={
            'error': str(exc),
            'request_id': request_id,
            'path': request.url.path
        }
    )
    
    # Don't expose internal error details in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            'error': 'Internal server error',
            'request_id': request_id,
            'message': 'An unexpected error occurred. Please try again later.'
        }
    )


def setup_error_handlers(app):
    """Register all error handlers with the FastAPI application"""
    
    # Custom API errors
    app.add_exception_handler(APIError, api_error_handler)
    
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    
    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Database errors
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    
    # General exceptions (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Error handlers registered successfully")
