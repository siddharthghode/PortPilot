"""Process inspection logic for PortPilot."""

import datetime
from pathlib import Path

import psutil

from portpilot.logger import get_logger
from portpilot.models import ProcessInfo

logger = get_logger()


def detect_systemd_service(pid: int) -> tuple[bool, str | None]:
    """Inspect /proc/<pid>/cgroup to identify systemd service association.

    Returns:
        (is_systemd, service_name_or_unit)
    """
    cgroup_file = Path(f"/proc/{pid}/cgroup")
    if not cgroup_file.is_file():
        return False, None

    try:
        content = cgroup_file.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            # Example cgroup v2: 0::/system.slice/postgresql.service
            # Example cgroup v1: 1:name=systemd:/system.slice/nginx.service
            if "system.slice/" in line:
                part = line.split("system.slice/")[1].split("/")[0]
                if part.endswith(".service"):
                    return True, part
                return True, part
            if ".service" in line:
                for token in line.split("/"):
                    if token.endswith(".service"):
                        return True, token
    except (OSError, PermissionError):
        pass

    return False, None


def detect_docker_container(pid: int, cmdline: list[str] | None = None) -> tuple[bool, str | None]:
    """Detect if process is running inside Docker or is docker-proxy forwarding.

    Returns:
        (is_docker, container_identifier_or_role)
    """
    # Check docker-proxy
    if cmdline and any("docker-proxy" in arg for arg in cmdline):
        return True, "docker-proxy (port forwarding)"

    cgroup_file = Path(f"/proc/{pid}/cgroup")
    if cgroup_file.is_file():
        try:
            content = cgroup_file.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                if "docker" in line or "containerd" in line:
                    # Extract container id if present (typically 64 hex chars)
                    parts = line.strip().split("/")
                    for p in parts:
                        if len(p) == 64 and all(c in "0123456789abcdefABCDEF" for c in p):
                            return True, f"container:{p[:12]}"
                    return True, "docker-managed container"
        except (OSError, PermissionError):
            pass

    return False, None


class ProcessInspector:
    """Safely inspects processes using psutil and Linux /proc pseudo-filesystem."""

    @staticmethod
    def inspect_pid(pid: int) -> ProcessInfo:
        """Inspect a single process by PID, handling disappearance or permission blocks."""
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return ProcessInfo(
                pid=pid,
                name="<process-exited>",
                status="terminated",
            )
        except psutil.AccessDenied:
            return ProcessInfo(
                pid=pid,
                name="<access-denied>",
                username="<restricted>",
            )

        name = "unknown"
        status = None
        ppid = None
        username = None
        exe = None
        cmdline = None
        create_time = None
        memory_rss = None
        cpu_percent = None

        # Safely retrieve process attributes
        try:
            name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        try:
            status = proc.status()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        try:
            ppid = proc.ppid()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        try:
            username = proc.username()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        try:
            exe = proc.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        try:
            cmdline = proc.cmdline()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        try:
            create_time = proc.create_time()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        try:
            mem_info = proc.memory_info()
            memory_rss = mem_info.rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        is_systemd, systemd_unit = detect_systemd_service(pid)
        is_docker, docker_id = detect_docker_container(pid, cmdline)

        return ProcessInfo(
            pid=pid,
            name=name,
            username=username,
            cmdline=cmdline,
            status=status,
            ppid=ppid,
            exe=exe,
            create_time=create_time,
            is_systemd=is_systemd,
            systemd_service=systemd_unit,
            is_docker=is_docker,
            docker_container_id=docker_id,
            memory_rss=memory_rss,
            cpu_percent=cpu_percent,
        )

    @classmethod
    def format_start_time(cls, create_time: float | None) -> str:
        """Format process creation timestamp into readable ISO format."""
        if not create_time:
            return "Unknown"
        try:
            dt = datetime.datetime.fromtimestamp(create_time, tz=datetime.UTC)
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            return "Unknown"
