"""Structured logging configuration with trace context support."""
import logging
import sys
from enum import Enum
from typing import Optional
from pathlib import Path

from pydantic import BaseModel


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogConfig(BaseModel):
    level: LogLevel = LogLevel.INFO
    format: str = "[{asctime}][{level}][{name}][trace_id={trace_id}] {message}"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_dir: Optional[str] = None


class TraceContext:
    _trace_id: Optional[str] = None

    @classmethod
    def set_trace_id(cls, trace_id: str):
        cls._trace_id = trace_id

    @classmethod
    def get_trace_id(cls) -> Optional[str]:
        return cls._trace_id

    @classmethod
    def clear(cls):
        cls._trace_id = None


class ContextAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        trace_id = TraceContext.get_trace_id()
        extra = self.extra.copy()
        extra["trace_id"] = trace_id or "-"
        return (
            msg.replace("{trace_id}", extra["trace_id"]),
            {"extra": extra},
        )


def setup_logging(
    name: str,
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[str] = None,
) -> ContextAdapter:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.value))

    if logger.handlers:
        return ContextAdapter(logger, {"trace_id": "-"})

    formatter = logging.Formatter(
        fmt="[{asctime}][{levelname}][{name}][trace_id={trace_id}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return ContextAdapter(logger, {"trace_id": "-"})


def get_logger(name: str) -> ContextAdapter:
    return setup_logging(name)
