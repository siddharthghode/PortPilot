"""Service registry for common development service port mappings."""

import json
from pathlib import Path
from typing import Any

from portpilot.logger import get_logger
from portpilot.models import Protocol, ServicePreset

logger = get_logger()

# Convention disclaimer constant
CONVENTION_DISCLAIMER = (
    "Note: Port associations are standard conventions and do not prove "
    "which application or process is actually running."
)


class ServiceRegistry:
    """Manages built-in and user-defined service port presets."""

    def __init__(self, custom_presets: list[ServicePreset] | None = None) -> None:
        self._presets: list[ServicePreset] = []
        self._load_defaults()
        if custom_presets:
            for preset in custom_presets:
                self.register(preset)

    def _load_defaults(self) -> None:
        """Load default services from embedded package JSON file."""
        pkg_data_path = Path(__file__).parent / "data" / "services.json"
        if not pkg_data_path.is_file():
            # Fallback to config directory in repo
            repo_config_path = Path(__file__).parent.parent / "config" / "services.json"
            if repo_config_path.is_file():
                pkg_data_path = repo_config_path

        if pkg_data_path.is_file():
            try:
                data = json.loads(pkg_data_path.read_text(encoding="utf-8"))
                for entry in data:
                    proto = (
                        Protocol.UDP
                        if str(entry.get("protocol", "tcp")).lower() == "udp"
                        else Protocol.TCP
                    )
                    self.register(
                        ServicePreset(
                            name=entry["name"],
                            port=int(entry["port"]),
                            protocol=proto,
                            category=entry.get("category", ""),
                            description=entry.get("description", ""),
                        )
                    )
            except Exception as err:
                logger.error("Failed to load default services from %s: %s", pkg_data_path, err)
                self._load_hardcoded_fallback()
        else:
            self._load_hardcoded_fallback()

    def _load_hardcoded_fallback(self) -> None:
        """Hardcoded defaults if json data file cannot be located."""
        defaults = [
            ("PostgreSQL", 5432, "database", "PostgreSQL database server"),
            ("MySQL", 3306, "database", "MySQL database server"),
            ("MariaDB", 3306, "database", "MariaDB database server"),
            ("MongoDB", 27017, "database", "MongoDB document database"),
            ("Redis", 6379, "cache", "Redis in-memory data store"),
            ("Elasticsearch", 9200, "search", "Elasticsearch search engine"),
            ("Kibana", 5601, "analytics", "Kibana visualization dashboard"),
            ("RabbitMQ", 5672, "queue", "RabbitMQ message broker"),
            ("RabbitMQ Management", 15672, "management", "RabbitMQ web management UI"),
            ("Django", 8000, "web-framework", "Django development server"),
            ("FastAPI", 8000, "web-framework", "FastAPI / Uvicorn development server"),
            ("Flask", 5000, "web-framework", "Flask development server"),
            ("Node.js", 3000, "web-framework", "Node.js application server"),
            ("Next.js", 3000, "web-framework", "Next.js development server"),
            ("React/Vite", 5173, "frontend", "Vite dev server (React/Vue/Svelte)"),
            ("Nginx", 80, "web-server", "HTTP web server / reverse proxy"),
            ("HTTPS", 443, "web-server", "Secure HTTP (TLS/SSL) server"),
        ]
        for name, port, cat, desc in defaults:
            self.register(
                ServicePreset(
                    name=name,
                    port=port,
                    protocol=Protocol.TCP,
                    category=cat,
                    description=desc,
                )
            )

    def register(self, preset: ServicePreset) -> None:
        """Register a service preset, avoiding exact duplicates (same name, port, protocol)."""
        for existing in self._presets:
            if (
                existing.name.lower() == preset.name.lower()
                and existing.port == preset.port
                and existing.protocol == preset.protocol
            ):
                # Update existing description and category
                existing.description = preset.description or existing.description
                existing.category = preset.category or existing.category
                return
        self._presets.append(preset)

    def get_services_for_port(
        self, port: int, protocol: Protocol = Protocol.TCP
    ) -> list[ServicePreset]:
        """Return all service presets associated with a given port and protocol."""
        return [p for p in self._presets if p.port == port and p.protocol == protocol]

    def get_service_names_for_port(self, port: int, protocol: Protocol = Protocol.TCP) -> list[str]:
        """Return names of all services associated with a given port and protocol."""
        return [p.name for p in self.get_services_for_port(port, protocol)]

    def get_all(self) -> list[ServicePreset]:
        """Return all registered service presets sorted by port and name."""
        return sorted(self._presets, key=lambda p: (p.port, p.name))

    def get_all_ports(self, protocol: Protocol = Protocol.TCP) -> list[int]:
        """Return unique sorted list of all ports in registry for given protocol."""
        return sorted({p.port for p in self._presets if p.protocol == protocol})

    def to_dict(self) -> list[dict[str, Any]]:
        """Return registry as list of dictionaries."""
        return [p.to_dict() for p in self.get_all()]
