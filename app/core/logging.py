"""Structured JSON logging for CloudWatch compatibility."""

from __future__ import annotations

import json
import logging
import sys
import traceback
from typing import Any


class JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        log_obj: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
        }

        # Inject extra fields propagated from the caller
        for key in ("request_id", "path", "method", "status_code", "duration_ms"):
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)

        if record.exc_info:
            log_obj["exception"] = "".join(traceback.format_exception(*record.exc_info))

        return json.dumps(log_obj)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON output to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Quieten noisy third-party loggers
    for noisy in ("boto3", "botocore", "urllib3", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
