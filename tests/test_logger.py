"""Unit tests for logger and log sanitization."""

import logging
from pathlib import Path

from portpilot.logger import SensitiveDataFilter, get_logger, setup_logger


def test_sensitive_data_filter():
    filt = SensitiveDataFilter()
    rec = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Database password='supersecretpass' connected",
        args=(),
        exc_info=None,
    )
    filt.filter(rec)
    assert "supersecretpass" not in rec.msg
    assert "password=********" in rec.msg


def test_setup_logger_debug_and_file(tmp_path: Path):
    log_file = tmp_path / "test.log"
    logger = setup_logger(
        name="test_logger",
        debug=True,
        log_file=log_file,
    )
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 2

    logger.debug("Debug event")
    content = log_file.read_text(encoding="utf-8")
    assert "Debug event" in content


def test_setup_logger_verbose():
    logger = setup_logger(
        name="test_verbose_logger",
        verbose=True,
    )
    assert logger.level == logging.INFO


def test_get_logger():
    l1 = get_logger("my_log")
    assert l1.name == "my_log"
