"""Docker Compose configuration parsing and host port preflight verification."""

from pathlib import Path
from typing import Any

import yaml

from portpilot.exceptions import ComposeError
from portpilot.logger import get_logger
from portpilot.models import (
    ComposePortMapping,
    ComposePreflightConflict,
    ComposePreflightResult,
    PortStatus,
    Protocol,
)
from portpilot.scanner import PortScanner
from portpilot.utils import substitute_env_vars, validate_port

logger = get_logger()

# Standard Compose file candidates according to Compose specification
COMPOSE_FILE_CANDIDATES = [
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
]


class DockerComposeChecker:
    """Parses Docker Compose configurations and verifies host port availability."""

    def __init__(self, scanner: PortScanner | None = None) -> None:
        self.scanner = scanner or PortScanner()

    def find_compose_file(self, explicit_path: str | Path | None = None) -> Path:
        """Locate Compose file from explicit path or directory defaults."""
        if explicit_path:
            p = Path(explicit_path).expanduser().resolve()
            if not p.is_file():
                raise ComposeError(f"Specified Compose file not found: {explicit_path}")
            return p

        cwd = Path.cwd()
        for candidate in COMPOSE_FILE_CANDIDATES:
            target = cwd / candidate
            if target.is_file():
                return target

        raise ComposeError(
            f"No Docker Compose file found in {cwd}. Looked for: {', '.join(COMPOSE_FILE_CANDIDATES)}"
        )

    def parse_compose_file(self, file_path: Path) -> tuple[list[ComposePortMapping], list[str]]:
        """Parse Compose YAML and extract host port mappings.

        Returns:
            (list_of_mappings, list_of_warnings)
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as err:
            raise ComposeError(f"Cannot read Compose file '{file_path}': {err}") from err

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as err:
            raise ComposeError(f"YAML syntax error in '{file_path}': {err}") from err

        if not isinstance(data, dict):
            raise ComposeError(
                f"Invalid Compose file structure in '{file_path}': root must be a mapping."
            )

        services = data.get("services")
        if not services or not isinstance(services, dict):
            return [], [f"No services defined in {file_path.name}"]

        mappings: list[ComposePortMapping] = []
        warnings: list[str] = []

        for service_name, svc_conf in services.items():
            if not isinstance(svc_conf, dict):
                continue

            ports_raw = svc_conf.get("ports", [])
            if not ports_raw:
                continue

            for port_entry in ports_raw:
                parsed_mappings, port_warnings = self._parse_port_entry(service_name, port_entry)
                mappings.extend(parsed_mappings)
                warnings.extend(port_warnings)

        return mappings, warnings

    def _parse_port_entry(
        self, service_name: str, entry: Any
    ) -> tuple[list[ComposePortMapping], list[str]]:
        """Parse a single ports entry (short syntax string or long syntax dict)."""
        mappings: list[ComposePortMapping] = []
        warnings: list[str] = []

        # Case 1: Long syntax dictionary
        # e.g.: {target: 80, published: 8080, protocol: "tcp", mode: "host"}
        if isinstance(entry, dict):
            target = entry.get("target")
            published = entry.get("published")
            proto_str = str(entry.get("protocol", "tcp")).lower()
            protocol = Protocol.UDP if proto_str == "udp" else Protocol.TCP
            host_ip = str(entry.get("host_ip", ""))

            if published is None:
                # Ephemeral dynamic port mapping
                return [
                    ComposePortMapping(
                        service_name=service_name,
                        host_ip=host_ip,
                        host_port=0,
                        container_port=int(target) if target else 0,
                        protocol=protocol,
                        is_dynamic=True,
                        raw_mapping=str(entry),
                    )
                ], warnings

            # Handle env vars in published port
            published_str, resolved = substitute_env_vars(str(published))
            if not resolved:
                warnings.append(
                    f"Service '{service_name}': Unresolved env variable in published port '{published}'. Cannot verify host port."
                )
                return [], warnings

            try:
                host_port = validate_port(published_str)
                container_port = int(target) if target else host_port
                mappings.append(
                    ComposePortMapping(
                        service_name=service_name,
                        host_ip=host_ip,
                        host_port=host_port,
                        container_port=container_port,
                        protocol=protocol,
                        is_dynamic=False,
                        raw_mapping=str(entry),
                    )
                )
            except Exception as err:
                warnings.append(
                    f"Service '{service_name}': Invalid long-form port '{published}': {err}"
                )
            return mappings, warnings

        # Case 2: Short syntax string or integer
        raw_str = str(entry).strip()
        substituted_str, resolved = substitute_env_vars(raw_str)
        if not resolved:
            warnings.append(
                f"Service '{service_name}': Unresolved env variable in port mapping '{raw_str}'."
            )
            return [], warnings

        # Protocol suffix: e.g. "/udp" or "/tcp"
        protocol = Protocol.TCP
        if "/" in substituted_str:
            base_str, proto_suffix = substituted_str.rsplit("/", 1)
            if proto_suffix.lower() == "udp":
                protocol = Protocol.UDP
        else:
            base_str = substituted_str

        # Parts separated by ":"
        parts = base_str.split(":")

        if len(parts) == 1:
            # Single port: e.g. "3000" -> docker binds ephemeral random host port
            try:
                c_port = int(parts[0])
                mappings.append(
                    ComposePortMapping(
                        service_name=service_name,
                        host_ip="",
                        host_port=0,
                        container_port=c_port,
                        protocol=protocol,
                        is_dynamic=True,
                        raw_mapping=raw_str,
                    )
                )
            except ValueError:
                warnings.append(
                    f"Service '{service_name}': Invalid port specification '{raw_str}'."
                )
            return mappings, warnings

        host_ip = ""
        host_port_part = ""
        container_port_part = ""

        if len(parts) == 2:
            # Format: "HOST:CONTAINER" (e.g. "8080:80")
            host_port_part = parts[0]
            container_port_part = parts[1]
        elif len(parts) == 3:
            # Format: "IP:HOST:CONTAINER" (e.g. "127.0.0.1:8080:80")
            host_ip = parts[0]
            host_port_part = parts[1]
            container_port_part = parts[2]
        else:
            warnings.append(f"Service '{service_name}': Unsupported port format '{raw_str}'.")
            return mappings, warnings

        # Check for port range in host:container (e.g. "3000-3002:3000-3002")
        if "-" in host_port_part:
            try:
                h_start, h_end = (int(x) for x in host_port_part.split("-"))
                c_start, c_end = (
                    (int(x) for x in container_port_part.split("-"))
                    if "-" in container_port_part
                    else (int(container_port_part), int(container_port_part))
                )

                for offset, h_p in enumerate(range(h_start, h_end + 1)):
                    c_p = c_start + offset if "-" in container_port_part else c_start
                    mappings.append(
                        ComposePortMapping(
                            service_name=service_name,
                            host_ip=host_ip,
                            host_port=validate_port(h_p),
                            container_port=validate_port(c_p),
                            protocol=protocol,
                            is_dynamic=False,
                            raw_mapping=raw_str,
                        )
                    )
            except Exception as err:
                warnings.append(
                    f"Service '{service_name}': Failed parsing port range '{raw_str}': {err}"
                )
            return mappings, warnings

        try:
            h_port = validate_port(host_port_part)
            c_port = validate_port(container_port_part)
            mappings.append(
                ComposePortMapping(
                    service_name=service_name,
                    host_ip=host_ip,
                    host_port=h_port,
                    container_port=c_port,
                    protocol=protocol,
                    is_dynamic=False,
                    raw_mapping=raw_str,
                )
            )
        except Exception as err:
            warnings.append(f"Service '{service_name}': Invalid port mapping '{raw_str}': {err}")

        return mappings, warnings

    def run_preflight(self, compose_file_path: str | Path | None = None) -> ComposePreflightResult:
        """Execute preflight port conflict check against the Compose file."""
        target_file = self.find_compose_file(compose_file_path)
        mappings, warnings = self.parse_compose_file(target_file)

        conflicts: list[ComposePreflightConflict] = []

        # Only static mappings with explicit host ports can conflict
        static_mappings = [m for m in mappings if not m.is_dynamic and m.host_port > 0]
        if not static_mappings:
            return ComposePreflightResult(
                compose_file=str(target_file),
                mappings=mappings,
                conflicts=[],
                warnings=warnings,
            )

        # Batch scan ports
        ports_to_check = list({m.host_port for m in static_mappings})
        scan_results = self.scanner.scan_ports(ports_to_check)
        results_by_port = {r.port: r for r in scan_results}

        for mapping in static_mappings:
            port_info = results_by_port.get(mapping.host_port)
            if port_info and port_info.status == PortStatus.OCCUPIED:
                conflicts.append(
                    ComposePreflightConflict(
                        service_name=mapping.service_name,
                        host_port=mapping.host_port,
                        host_ip=mapping.host_ip,
                        protocol=mapping.protocol,
                        port_info=port_info,
                    )
                )

        return ComposePreflightResult(
            compose_file=str(target_file),
            mappings=mappings,
            conflicts=conflicts,
            warnings=warnings,
        )
