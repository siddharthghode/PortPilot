"""Structured logging module for PortPilot."""

import logging
import re
import sys
from pathlib import Path

# Pattern for masking potentially sensitive values (tokens, passwords, keys)
SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|token|secret|api[_-]?key|credential|auth)[\"':=\s]+([^\s\"'&]+)",
    re.IGNORECASE,
)


class SensitiveDataFilter(logging.Filter):
    """Filter to sanitize sensitive patterns from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = SENSITIVE_KEY_PATTERN.sub(r"\1=********", record.msg)
        return True


def setup_logger(
    name: str = "portpilot",
    verbose: bool = False,
    debug: bool = False,
    log_file: str | Path | None = None,
) -> logging.Logger:
    """Configure and return the PortPilot application logger.

    Args:
        name: Logger name.
        verbose: If True, set level to INFO.
        debug: If True, set level to DEBUG.
        log_file: Optional path to write log output.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        logger.handlers.clear()

    level = logging.WARNING
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO

    logger.setLevel(level)

    # Console formatter
    console_format = "%(levelname)s: %(message)s"
    if debug:
        console_format = (
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        )

    formatter = logging.Formatter(console_format)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(console_handler)

    if log_file:
        try:
            log_path = Path(log_file).expanduser().resolve()
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
            file_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s (%(process)d): %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            file_handler.addFilter(SensitiveDataFilter())
            logger.addHandler(file_handler)
        except OSError as err:
            logger.warning("Failed to initialize log file '%s': %s", log_file, err)

    return logger


def get_logger(name: str = "portpilot") -> logging.Logger:
    """Retrieve existing logger or configure default."""
    return logging.getLogger(name)
