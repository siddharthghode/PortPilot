"""Configuration management for PortPilot."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from portpilot.exceptions import ConfigError
from portpilot.logger import get_logger
from portpilot.models import Protocol, ServicePreset

logger = get_logger()

# Use standard tomllib in Python 3.11+
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_PORTS = [
    80,
    443,
    3000,
    3306,
    5000,
    5173,
    5432,
    5601,
    5672,
    6379,
    8000,
    9200,
    15672,
    27017,
]


@dataclass
class Config:
    """Application configuration state."""

    default_ports: list[int] = field(default_factory=lambda: list(DEFAULT_PORTS))
    custom_services: list[ServicePreset] = field(default_factory=list)
    termination_timeout: float = 5.0
    color: bool = True
    default_protocol: Protocol = Protocol.TCP

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "Config":
        """Load configuration from the specified path or standard search locations."""
        target_path = cls._find_config_file(config_path)
        if not target_path:
            logger.debug("No configuration file found; using default settings.")
            return cls()

        logger.debug("Loading configuration from: %s", target_path)
        try:
            content = target_path.read_text(encoding="utf-8")
            if target_path.suffix.lower() == ".json":
                data = json.loads(content)
            elif target_path.suffix.lower() in (".toml", ".tml"):
                data = tomllib.loads(content)
            else:
                # Attempt to parse as TOML first, fallback to JSON
                try:
                    data = tomllib.loads(content)
                except Exception:
                    data = json.loads(content)
        except Exception as err:
            raise ConfigError(f"Failed to parse configuration file '{target_path}': {err}") from err

        return cls._from_dict(data)

    @classmethod
    def _find_config_file(cls, explicit_path: str | Path | None) -> Path | None:
        """Locate the configuration file based on precedence rules."""
        if explicit_path:
            p = Path(explicit_path).expanduser().resolve()
            if not p.is_file():
                raise ConfigError(f"Specified configuration file does not exist: {explicit_path}")
            return p

        # Check environment variable
        env_config = os.environ.get("PORTPILOT_CONFIG")
        if env_config:
            p = Path(env_config).expanduser().resolve()
            if p.is_file():
                return p

        # Check standard user locations
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        config_dir = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"

        user_candidates = [
            config_dir / "portpilot" / "config.toml",
            config_dir / "portpilot" / "config.json",
            Path.home() / ".portpilot.toml",
            Path.home() / ".portpilot.json",
        ]
        for candidate in user_candidates:
            if candidate.is_file():
                return candidate

        # System-wide candidates
        system_candidates = [
            Path("/etc/portpilot/config.toml"),
            Path("/etc/portpilot/config.json"),
        ]
        for candidate in system_candidates:
            if candidate.is_file():
                return candidate

        return None

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Config":
        """Instantiate Config from parsed dictionary data."""
        default_ports = data.get("default_ports", list(DEFAULT_PORTS))
        if not isinstance(default_ports, list):
            raise ConfigError("'default_ports' must be a list of integers.")

        termination_timeout = float(data.get("termination_timeout", 5.0))
        color = bool(data.get("color", True))
        protocol_str = str(data.get("default_protocol", "tcp")).lower()
        protocol = Protocol.UDP if protocol_str == "udp" else Protocol.TCP

        custom_services: list[ServicePreset] = []
        services_raw = data.get("services", [])
        if isinstance(services_raw, list):
            for item in services_raw:
                if isinstance(item, dict) and "name" in item and "port" in item:
                    proto_val = (
                        Protocol.UDP
                        if str(item.get("protocol", "tcp")).lower() == "udp"
                        else Protocol.TCP
                    )
                    custom_services.append(
                        ServicePreset(
                            name=str(item["name"]),
                            port=int(item["port"]),
                            protocol=proto_val,
                            category=str(item.get("category", "custom")),
                            description=str(item.get("description", "")),
                        )
                    )

        return cls(
            default_ports=[int(p) for p in default_ports],
            custom_services=custom_services,
            termination_timeout=termination_timeout,
            color=color,
            default_protocol=protocol,
        )
