"""Exception definitions for PortPilot."""


class PortPilotError(Exception):
    """Base exception for all PortPilot errors."""


class PortValidationError(PortPilotError):
    """Raised when a port number or range is invalid."""


class ProcessPermissionError(PortPilotError):
    """Raised when process inspection or termination is blocked by OS permissions."""


class ProcessTerminationError(PortPilotError):
    """Raised when a process fails to terminate within the grace period."""


class CriticalProcessError(PortPilotError):
    """Raised when an operation targets a protected or critical process (e.g. PID 1, self)."""


class ConfigError(PortPilotError):
    """Raised when a configuration file cannot be read or parsed."""


class ComposeError(PortPilotError):
    """Raised when a Docker Compose file is invalid or cannot be parsed."""


class SocketInspectionError(PortPilotError):
    """Raised when socket table inspection encounters an unexpected failure."""
