"""Unit tests for portpilot.utils."""

import pytest

from portpilot.exceptions import PortValidationError
from portpilot.formatter import pad_ansi, strip_ansi
from portpilot.utils import (
    Colorizer,
    is_root,
    parse_port_range,
    parse_ports,
    substitute_env_vars,
    validate_port,
)


def test_validate_port_valid():
    assert validate_port(1) == 1
    assert validate_port(80) == 80
    assert validate_port(65535) == 65535
    assert validate_port("8080") == 8080


def test_validate_port_invalid():
    with pytest.raises(PortValidationError, match="must be an integer"):
        validate_port("invalid")

    with pytest.raises(PortValidationError, match="out of valid range"):
        validate_port(0)

    with pytest.raises(PortValidationError, match="out of valid range"):
        validate_port(65536)

    with pytest.raises(PortValidationError, match="out of valid range"):
        validate_port(-80)


def test_parse_ports_valid():
    assert parse_ports("80,443,8080") == [80, 443, 8080]
    assert parse_ports("5432") == [5432]
    # Duplicates removed preserving order
    assert parse_ports("80,80,443") == [80, 443]
    # Embedded range
    assert parse_ports("80, 3000-3002") == [80, 3000, 3001, 3002]


def test_parse_ports_invalid():
    with pytest.raises(PortValidationError, match="Empty port list"):
        parse_ports("")

    with pytest.raises(PortValidationError, match="No valid ports"):
        parse_ports(" , , ")

    with pytest.raises(PortValidationError):
        parse_ports("80, invalid")


def test_parse_port_range_valid():
    assert parse_port_range("3000-3003") == [3000, 3001, 3002, 3003]
    assert parse_port_range("80-80") == [80]


def test_parse_port_range_invalid():
    with pytest.raises(PortValidationError, match="Invalid port range"):
        parse_port_range("3000")

    with pytest.raises(PortValidationError, match="Multiple hyphens"):
        parse_port_range("3000-4000-5000")

    with pytest.raises(PortValidationError, match="cannot exceed end"):
        parse_port_range("8000-3000")

    with pytest.raises(PortValidationError, match="exceeding limit"):
        parse_port_range("1-20000", max_ports=100)


def test_substitute_env_vars():
    env = {"PORT": "8080", "HOST": "localhost"}

    # Standard ${VAR}
    res, ok = substitute_env_vars("${PORT}", env)
    assert res == "8080"
    assert ok is True

    # Default fallback ${VAR:-default}
    res, ok = substitute_env_vars("${UNSET:-9000}", env)
    assert res == "9000"
    assert ok is True

    # Unresolved variable
    res, ok = substitute_env_vars("${MISSING}", env)
    assert res == "${MISSING}"
    assert ok is False

    # Short syntax $VAR
    res, ok = substitute_env_vars("$HOST", env)
    assert res == "localhost"
    assert ok is True


def test_colorizer_enabled_and_disabled():
    c_on = Colorizer(enabled=True)
    assert isinstance(c_on.enabled, bool)
    c_off = Colorizer(enabled=False)
    assert c_off.red("test") == "test"
    assert c_off.green("test") == "test"
    assert c_off.bold("test") == "test"
    assert c_off.pass_badge() == "[PASS]"
    assert c_off.fail_badge() == "[FAIL]"
    assert c_off.warn_badge() == "[WARN]"
    assert c_off.info_badge() == "[INFO]"


def test_ansi_pad_and_strip():
    colored = "\033[32m[PASS]\033[0m"
    assert strip_ansi(colored) == "[PASS]"
    padded = pad_ansi(colored, 10)
    assert strip_ansi(padded) == "[PASS]    "
    assert len(strip_ansi(padded)) == 10


def test_is_root():
    # Calling is_root() returns bool without exception
    assert isinstance(is_root(), bool)
