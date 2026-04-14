"""
Structured logging configuration using structlog.
Outputs JSON in production and pretty-printed logs in development.
"""
import logging
import sys

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """Configure structlog for the application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Standard library logging setup
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        # JSON output for log aggregation (Datadog, CloudWatch, etc.)
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        # Human-readable output for local development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__):
    """Return a bound structlog logger for the given module name."""
    return structlog.get_logger(name)
