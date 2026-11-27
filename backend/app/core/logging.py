"""JSON logging configuration with structured output."""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Optional

import structlog
from pythonjsonlogger import jsonlogger

from backend.app.core.config import settings


class RequestIdFilter(logging.Filter):
    """Add request_id to log records if available."""

    def filter(self, record: logging.LogRecord) -> bool:
        # request_id will be added by middleware
        return True


def setup_logging() -> None:
    """Configure structured JSON logging for the application."""

    # Standard library logging
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)

    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if settings.log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s",
            timestamp=True,
            rename_fields={
                "levelname": "level",
                "name": "logger",
            },
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if configured
    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)


class LoggingMixin:
    """Mixin to add structured logging to classes."""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__ + "." + self.__class__.__name__)
        return self._logger


def log_request(
    logger: structlog.stdlib.BoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log HTTP request with structured fields."""
    logger.info(
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        request_id=request_id,
        user_id=user_id,
        tenant_id=tenant_id,
        **kwargs,
    )


def log_error(
    logger: structlog.stdlib.BoundLogger,
    error: Exception,
    context: Optional[dict] = None,
    request_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log error with structured fields."""
    logger.error(
        "error",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        request_id=request_id,
        **kwargs,
    )


def log_business_event(
    logger: structlog.stdlib.BoundLogger,
    event: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log business event with structured fields."""
    logger.info(
        "business_event",
        event=event,
        request_id=request_id,
        user_id=user_id,
        tenant_id=tenant_id,
        **kwargs,
    )