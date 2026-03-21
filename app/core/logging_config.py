"""
Logging configuration for Veritariff API.

In production (environment != "local") logs are emitted as JSON so they can be
ingested by Datadog / CloudWatch / GCP Logging without a parser.

In local/dev mode logs are emitted in a human-readable coloured format.
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# JSON formatter (used in production)
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    RESERVED = {"message", "timestamp", "level", "logger", "exc_info", "exc_text", "stack_info"}

    def format(self, record: logging.LogRecord) -> str:
        obj: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach any extra fields passed via logger.info("msg", extra={...})
        for key, val in record.__dict__.items():
            if key.startswith("_") or key in logging.LogRecord.__dict__ or key in self.RESERVED:
                continue
            if key in ("args", "created", "exc_info", "exc_text", "filename",
                       "funcName", "levelname", "levelno", "lineno", "module",
                       "msecs", "msg", "name", "pathname", "process",
                       "processName", "relativeCreated", "stack_info",
                       "taskName", "thread", "threadName"):
                continue
            obj[key] = val

        if record.exc_info:
            obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(obj, default=str)


# ---------------------------------------------------------------------------
# Readable formatter (used locally)
# ---------------------------------------------------------------------------

_GREY = "\x1b[38;5;240m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"
_BOLD_RED = "\x1b[31;1m"
_RESET = "\x1b[0m"

_LEVEL_COLOURS = {
    "DEBUG": _GREY,
    "INFO": _GREEN,
    "WARNING": _YELLOW,
    "ERROR": _RED,
    "CRITICAL": _BOLD_RED,
}


class ReadableFormatter(logging.Formatter):
    FMT = "%(asctime)s  {colour}%(levelname)-8s{reset}  %(name)-35s  %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        colour = _LEVEL_COLOURS.get(record.levelname, "")
        fmt = self.FMT.format(colour=colour, reset=_RESET)
        formatter = logging.Formatter(fmt, datefmt="%H:%M:%S")
        result = formatter.format(record)

        # Append any extra context keys on the same line
        extras = []
        skip = {
            "args", "created", "exc_info", "exc_text", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs", "msg",
            "name", "pathname", "process", "processName", "relativeCreated",
            "stack_info", "taskName", "thread", "threadName", "message",
        }
        for key, val in record.__dict__.items():
            if key.startswith("_") or key in skip or key in logging.LogRecord.__dict__:
                continue
            extras.append(f"{key}={val!r}")
        if extras:
            result += "  |  " + "  ".join(extras)

        return result


# ---------------------------------------------------------------------------
# Public setup function
# ---------------------------------------------------------------------------

def configure_logging(environment: str = "local", log_level: str = "INFO") -> None:
    """
    Call once at application startup (before any logger is used).

    Args:
        environment: "local" → readable format; anything else → JSON.
        log_level:   Root log level string, e.g. "DEBUG", "INFO", "WARNING".
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if environment == "local":
        handler.setFormatter(ReadableFormatter())
    else:
        handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if log_level.upper() == "DEBUG" else logging.WARNING
    )
