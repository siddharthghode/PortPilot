"""Utility functions for port validation, parsing, formatting, and OS checks."""

import os
import re
import sys
from typing import Any

from portpilot.exceptions import PortValidationError

# ANSI Escape Codes
_ANSI_RESET = "\033[0m"
_ANSI_BOLD = "\033[1m"
_ANSI_RED = "\033[31m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_BLUE = "\033[34m"
_ANSI_CYAN = "\033[36m"
_ANSI_GRAY = "\033[90m"


class Colorizer:
    """Manages terminal colors with support for disabling via flag or NO_COLOR."""

    def __init__(self, enabled: bool = True) -> None:
        # Respect NO_COLOR env var (https://no-color.org) and non-tty streams
        no_color_env = bool(os.environ.get("NO_COLOR"))
        is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        self.enabled = enabled and not no_color_env and is_tty

    def bold(self, text: Any) -> str:
        return f"{_ANSI_BOLD}{text}{_ANSI_RESET}" if self.enabled else str(text)

    def red(self, text: Any) -> str:
        return f"{_ANSI_RED}{text}{_ANSI_RESET}" if self.enabled else str(text)

    def green(self, text: Any) -> str:
        return f"{_ANSI_GREEN}{text}{_ANSI_RESET}" if self.enabled else str(text)

    def yellow(self, text: Any) -> str:
        return f"{_ANSI_YELLOW}{text}{_ANSI_RESET}" if self.enabled else str(text)

    def blue(self, text: Any) -> str:
        return f"{_ANSI_BLUE}{text}{_ANSI_RESET}" if self.enabled else str(text)

    def cyan(self, text: Any) -> str:
        return f"{_ANSI_CYAN}{text}{_ANSI_RESET}" if self.enabled else str(text)

    def gray(self, text: Any) -> str:
        return f"{_ANSI_GRAY}{text}{_ANSI_RESET}" if self.enabled else str(text)

    def pass_badge(self) -> str:
        return self.green("[PASS]") if self.enabled else "[PASS]"

    def fail_badge(self) -> str:
        return self.red("[FAIL]") if self.enabled else "[FAIL]"

    def warn_badge(self) -> str:
        return self.yellow("[WARN]") if self.enabled else "[WARN]"

    def info_badge(self) -> str:
        return self.blue("[INFO]") if self.enabled else "[INFO]"


def validate_port(port: int | str) -> int:
    """Validate a single network port number.

    Must be an integer between 1 and 65535 inclusive.
    """
    try:
        val = int(port)
    except (ValueError, TypeError) as err:
        raise PortValidationError(f"Invalid port value '{port}': must be an integer.") from err

    if val < 1 or val > 65535:
        raise PortValidationError(f"Port {val} out of valid range (1-65535).")
    return val


def parse_ports(ports_str: str) -> list[int]:
    """Parse a comma-separated list of ports.

    Example: "5432,6379,8000" -> [5432, 6379, 8000]
    """
    if not ports_str or not ports_str.strip():
        raise PortValidationError("Empty port list provided.")

    ports: list[int] = []
    seen = set()
    tokens = [t.strip() for t in ports_str.split(",") if t.strip()]
    if not tokens:
        raise PortValidationError("No valid ports provided.")

    for token in tokens:
        # Check if single token is a range
        if "-" in token:
            range_ports = parse_port_range(token)
            for p in range_ports:
                if p not in seen:
                    seen.add(p)
                    ports.append(p)
        else:
            p = validate_port(token)
            if p not in seen:
                seen.add(p)
                ports.append(p)

    return ports


def parse_port_range(range_str: str, max_ports: int = 10000) -> list[int]:
    """Parse a port range string formatted as START-END.

    Example: "3000-3010" -> [3000, 3001, ..., 3010]
    """
    if not range_str or "-" not in range_str:
        raise PortValidationError(
            f"Invalid port range '{range_str}'. Expected format: START-END (e.g. 3000-8000)."
        )

    parts = range_str.split("-")
    if len(parts) != 2:
        raise PortValidationError(
            f"Invalid port range format '{range_str}'. Multiple hyphens detected."
        )

    start = validate_port(parts[0].strip())
    end = validate_port(parts[1].strip())

    if start > end:
        raise PortValidationError(
            f"Invalid port range '{range_str}': start ({start}) cannot exceed end ({end})."
        )

    count = end - start + 1
    if count > max_ports:
        raise PortValidationError(
            f"Port range '{range_str}' contains {count} ports, exceeding limit of {max_ports}."
        )

    return list(range(start, end + 1))


def is_root() -> bool:
    """Return True if running as root/superuser."""
    return os.geteuid() == 0 if hasattr(os, "geteuid") else False


def substitute_env_vars(val: str, env: dict[str, str] | None = None) -> tuple[str, bool]:
    """Conservatively substitute environment variables in format ${VAR} or ${VAR:-default} or $VAR.

    Returns (substituted_string, all_resolved_bool).
    """
    if env is None:
        env = dict(os.environ)

    pattern = re.compile(r"\$\{([A-Za-z0-9_]+)(?::-([^}]*))?\}|\$([A-Za-z0-9_]+)")
    unresolved = False

    def replace_match(m: re.Match) -> str:
        nonlocal unresolved
        var_name = m.group(1) or m.group(3)
        default_val = m.group(2)

        if var_name in env:
            return env[var_name]
        if default_val is not None:
            return default_val
        unresolved = True
        return m.group(0)

    result = pattern.sub(replace_match, val)
    return result, not unresolved
