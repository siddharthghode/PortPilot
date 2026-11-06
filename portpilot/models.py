"""Data models for PortPilot."""

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Protocol(StrEnum):
    """Supported network transport protocols."""

    TCP = "tcp"
    UDP = "udp"

    def __str__(self) -> str:
        return self.value.upper()


class PortStatus(StrEnum):
    """Occupancy status of a network port."""

    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        return self.value


@dataclass
class ProcessInfo:
    """Detailed information about an OS process owning a port."""

    pid: int
    name: str
    username: str | None = None
    cmdline: list[str] | None = None
    status: str | None = None
    ppid: int | None = None
    exe: str | None = None
    create_time: float | None = None
    is_systemd: bool = False
    systemd_service: str | None = None
    is_docker: bool = False
    docker_container_id: str | None = None
    docker_container_name: str | None = None
    memory_rss: int | None = None
    cpu_percent: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert process info to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ServicePreset:
    """Predefined or user-configured service port association."""

    name: str
    port: int
    protocol: Protocol = Protocol.TCP
    category: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert preset to dictionary."""
        return {
            "name": self.name,
            "port": self.port,
            "protocol": self.protocol.value,
            "category": self.category,
            "description": self.description,
        }


@dataclass
class PortInfo:
    """Information regarding a single scanned port."""

    port: int
    protocol: Protocol
    status: PortStatus
    local_address: str | None = None
    remote_address: str | None = None
    processes: list[ProcessInfo] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert port info to dictionary for JSON output."""
        return {
            "port": self.port,
            "protocol": self.protocol.value,
            "status": self.status.value,
            "local_address": self.local_address,
            "remote_address": self.remote_address,
            "processes": [p.to_dict() for p in self.processes],
            "services": self.services,
            "error": self.error,
        }


@dataclass
class ComposePortMapping:
    """Port mapping extracted from a Docker Compose service definition."""

    service_name: str
    host_ip: str
    host_port: int
    container_port: int
    protocol: Protocol = Protocol.TCP
    is_dynamic: bool = False
    raw_mapping: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert port mapping to dictionary."""
        return {
            "service_name": self.service_name,
            "host_ip": self.host_ip,
            "host_port": self.host_port,
            "container_port": self.container_port,
            "protocol": self.protocol.value,
            "is_dynamic": self.is_dynamic,
            "raw_mapping": self.raw_mapping,
        }


@dataclass
class ComposePreflightConflict:
    """Details of a conflict between Docker Compose port requirement and host state."""

    service_name: str
    host_port: int
    host_ip: str
    protocol: Protocol
    port_info: PortInfo

    def to_dict(self) -> dict[str, Any]:
        """Convert conflict to dictionary."""
        return {
            "service_name": self.service_name,
            "host_port": self.host_port,
            "host_ip": self.host_ip,
            "protocol": self.protocol.value,
            "port_info": self.port_info.to_dict(),
        }


@dataclass
class ComposePreflightResult:
    """Aggregated result of a Docker Compose preflight inspection."""

    compose_file: str
    mappings: list[ComposePortMapping] = field(default_factory=list)
    conflicts: list[ComposePreflightConflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        """Return True if any host port conflict was detected."""
        return len(self.conflicts) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert preflight result to dictionary."""
        return {
            "compose_file": self.compose_file,
            "mappings": [m.to_dict() for m in self.mappings],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "warnings": self.warnings,
            "has_conflicts": self.has_conflicts,
        }


@dataclass
class StopResult:
    """Outcome of attempting to stop a process on a port."""

    port: int
    pid: int
    process_name: str
    signal_sent: str
    success: bool
    port_freed: bool
    message: str
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert stop result to dictionary."""
        return asdict(self)
