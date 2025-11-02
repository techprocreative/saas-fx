"""
Structured Logging Configuration
Implements Phase 1.3 of Production Roadmap
"""
import logging
import sys
import structlog
from pythonjsonlogger import jsonlogger
from datetime import datetime
from typing import Any, Dict
import traceback

from .config import settings


def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to log entries"""
    # Get from context if available
    if 'request_id' in event_dict:
        event_dict['correlation_id'] = event_dict['request_id']
    return event_dict


def add_timestamp(logger, method_name, event_dict):
    """Add ISO timestamp to log entries"""
    event_dict['timestamp'] = datetime.utcnow().isoformat()
    return event_dict


def add_log_level(logger, method_name, event_dict):
    """Normalize log level"""
    if method_name == 'warn':
        event_dict['level'] = 'WARNING'
    else:
        event_dict['level'] = method_name.upper()
    return event_dict


def add_exception_info(logger, method_name, event_dict):
    """Add exception traceback if present"""
    if event_dict.get('exc_info'):
        event_dict['exception'] = {
            'type': event_dict['exc_info'][0].__name__,
            'message': str(event_dict['exc_info'][1]),
            'traceback': ''.join(traceback.format_exception(*event_dict['exc_info']))
        }
        del event_dict['exc_info']
    return event_dict


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging"""
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['service'] = 'forex-ai-backend'
        
        # Add context fields
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'trace_id'):
            log_record['trace_id'] = record.trace_id
        
        # Add exception info
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }


def setup_logging():
    """Configure structured logging for the application"""
    
    # Configure standard logging
    logging.basicConfig(
        format='%(message)s',
        level=getattr(logging, settings.LOG_LEVEL),
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/app.log'),
            logging.FileHandler('logs/errors.log', level=logging.ERROR),
        ]
    )
    
    # Configure JSON logging for production
    if not settings.DEBUG:
        json_handler = logging.StreamHandler(sys.stdout)
        json_handler.setFormatter(CustomJsonFormatter())
        
        root_logger = logging.getLogger()
        root_logger.handlers = [json_handler]
        root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            add_log_level,
            add_timestamp,
            add_correlation_id,
            add_exception_info,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.info("Logging configuration initialized successfully")


def get_logger(name: str = None):
    """Get a configured logger instance"""
    return structlog.get_logger(name) if name else structlog.get_logger()


class LoggerAdapter:
    """Adapter for adding context to logger"""
    
    def __init__(self, logger, extra: Dict[str, Any] = None):
        self.logger = logger
        self.extra = extra or {}
    
    def _log(self, level: str, msg: str, **kwargs):
        """Internal log method with context"""
        log_data = {**self.extra, **kwargs}
        getattr(self.logger, level)(msg, **log_data)
    
    def debug(self, msg: str, **kwargs):
        self._log('debug', msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        self._log('info', msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        self._log('warning', msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        self._log('error', msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        self._log('critical', msg, **kwargs)
    
    def bind(self, **kwargs):
        """Create new logger with additional context"""
        new_extra = {**self.extra, **kwargs}
        return LoggerAdapter(self.logger, new_extra)


def get_request_logger(request_id: str = None, user_id: str = None):
    """Get logger with request context"""
    logger = get_logger(__name__)
    context = {}
    
    if request_id:
        context['request_id'] = request_id
    if user_id:
        context['user_id'] = user_id
    
    return LoggerAdapter(logger, context)


# Audit logging helpers
class AuditLogger:
    """Specialized logger for audit trails"""
    
    def __init__(self):
        self.logger = get_logger('audit')
        self.audit_handler = logging.FileHandler('logs/audit.log')
        self.audit_handler.setFormatter(CustomJsonFormatter())
    
    def log_user_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        status: str,
        details: Dict[str, Any] = None
    ):
        """Log user action for audit trail"""
        self.logger.info(
            f"User action: {action}",
            user_id=user_id,
            action=action,
            resource=resource,
            status=status,
            details=details or {},
            audit=True
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        source_ip: str,
        details: Dict[str, Any] = None
    ):
        """Log security event"""
        self.logger.warning(
            f"Security event: {event_type}",
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            details=details or {},
            security=True
        )
    
    def log_system_event(
        self,
        event: str,
        component: str,
        status: str,
        details: Dict[str, Any] = None
    ):
        """Log system event"""
        self.logger.info(
            f"System event: {event}",
            event=event,
            component=component,
            status=status,
            details=details or {},
            system=True
        )


audit_logger = AuditLogger()
