"""Safe process termination manager with safety guards and verification."""

import os
import signal
import time

import psutil

from portpilot.exceptions import CriticalProcessError, ProcessPermissionError
from portpilot.inspector import ProcessInspector
from portpilot.logger import get_logger
from portpilot.models import PortStatus, ProcessInfo, Protocol, StopResult
from portpilot.scanner import PortScanner

logger = get_logger()

# Known critical process names and patterns that warrant special warnings
DATABASE_PROCESS_NAMES = {
    "postgres",
    "postgresql",
    "mysqld",
    "mariadbd",
    "mongod",
    "redis-server",
    "dockerd",
    "containerd",
}


class ProcessManager:
    """Handles safe process termination with strict safety guarantees."""

    def __init__(self, scanner: PortScanner | None = None) -> None:
        self.scanner = scanner or PortScanner()
        self.inspector = ProcessInspector()

    def get_port_processes(self, port: int, protocol: Protocol = Protocol.TCP) -> list[ProcessInfo]:
        """Find all processes occupying the specified port."""
        port_info = self.scanner.scan_port(port, protocol)
        return port_info.processes

    def validate_target_process(self, proc_info: ProcessInfo) -> None:
        """Enforce safety rules before any termination attempt.

        Raises:
            CriticalProcessError: If the process is protected or critical.
            ProcessPermissionError: If target cannot be accessed due to permissions.
        """
        pid = proc_info.pid

        # Guard 1: Never kill PID 1 or kernel PID 0
        if pid <= 1:
            raise CriticalProcessError(
                f"Refusing to terminate PID {pid}: target is init / system manager."
            )

        # Guard 2: Never kill PortPilot itself or its parent
        current_pid = os.getpid()
        parent_pid = os.getppid()
        if pid == current_pid:
            raise CriticalProcessError(
                f"Refusing to terminate PID {pid}: target is the active PortPilot process."
            )
        if pid == parent_pid:
            raise CriticalProcessError(
                f"Refusing to terminate PID {pid}: target is the parent process of PortPilot."
            )

        # Guard 3: Validate process existence and identity (PID reuse check)
        try:
            live_proc = psutil.Process(pid)
        except psutil.NoSuchProcess as err:
            raise CriticalProcessError(f"Process PID {pid} no longer exists.") from err
        except psutil.AccessDenied as err:
            raise ProcessPermissionError(
                f"Access denied inspecting PID {pid}. Elevated privileges (sudo) required."
            ) from err

        if proc_info.create_time is not None:
            try:
                live_create_time = live_proc.create_time()
                # Compare creation times with a small tolerance for floating point
                if abs(live_create_time - proc_info.create_time) > 0.1:
                    raise CriticalProcessError(
                        f"PID reuse detected for PID {pid}! Process identity has changed."
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def check_safety_warnings(self, proc_info: ProcessInfo) -> list[str]:
        """Generate warnings for potentially sensitive or managed processes."""
        warnings: list[str] = []

        # Systemd warning
        if proc_info.is_systemd:
            unit = proc_info.systemd_service or "systemd unit"
            warnings.append(
                f"Process PID {proc_info.pid} is managed by systemd ({unit}). "
                f"Directly terminating it may cause systemd to automatically restart it. "
                f"Recommended action: sudo systemctl stop {unit}"
            )

        # Docker warning
        if proc_info.is_docker:
            container = proc_info.docker_container_id or "Docker container"
            warnings.append(
                f"Process PID {proc_info.pid} is managed by Docker ({container}). "
                f"Recommended action: docker stop {container} or docker-compose down"
            )

        # Database warning
        proc_name_lower = (proc_info.name or "").lower()
        if any(db in proc_name_lower for db in DATABASE_PROCESS_NAMES):
            warnings.append(
                f"Process '{proc_info.name}' appears to be a database or stateful server. "
                f"Terminating it may cause uncommitted transactions or data inconsistency."
            )

        return warnings

    def terminate_process(
        self,
        port: int,
        proc_info: ProcessInfo,
        timeout: float = 5.0,
        dry_run: bool = False,
        use_sigkill: bool = False,
        protocol: Protocol = Protocol.TCP,
    ) -> StopResult:
        """Safely terminate a validated process and verify port state."""
        self.validate_target_process(proc_info)
        pid = proc_info.pid

        if dry_run:
            sig = "SIGKILL" if use_sigkill else "SIGTERM"
            return StopResult(
                port=port,
                pid=pid,
                process_name=proc_info.name,
                signal_sent="NONE",
                success=True,
                port_freed=False,
                message=f"[DRY-RUN] Would send {sig} to PID {pid} ({proc_info.name}).",
                dry_run=True,
            )

        target_signal = signal.SIGKILL if use_sigkill else signal.SIGTERM
        sig_name = "SIGKILL" if use_sigkill else "SIGTERM"

        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return StopResult(
                port=port,
                pid=pid,
                process_name=proc_info.name,
                signal_sent="NONE",
                success=True,
                port_freed=self._is_port_freed(port, protocol),
                message=f"Process PID {pid} has already exited.",
            )
        except psutil.AccessDenied as err:
            raise ProcessPermissionError(
                f"Permission denied accessing PID {pid} to terminate it."
            ) from err

        # Send termination signal without shell
        try:
            logger.info("Sending %s to PID %d (%s)...", sig_name, pid, proc_info.name)
            proc.send_signal(target_signal)
        except ProcessLookupError:
            pass  # Already terminated
        except PermissionError as err:
            raise ProcessPermissionError(
                f"Permission denied sending {sig_name} to PID {pid}. Run with elevated privileges."
            ) from err

        # Wait for graceful exit within timeout
        exited = self._wait_for_exit(proc, timeout)

        if not exited:
            return StopResult(
                port=port,
                pid=pid,
                process_name=proc_info.name,
                signal_sent=sig_name,
                success=False,
                port_freed=False,
                message=(
                    f"Process PID {pid} ({proc_info.name}) did not terminate within {timeout}s grace period. "
                    f"You may escalate with SIGKILL."
                ),
            )

        # Process exited; verify port availability
        port_freed = self._is_port_freed(port, protocol)
        return StopResult(
            port=port,
            pid=pid,
            process_name=proc_info.name,
            signal_sent=sig_name,
            success=True,
            port_freed=port_freed,
            message=f"Process PID {pid} ({proc_info.name}) successfully terminated via {sig_name}.",
        )

    def _wait_for_exit(self, proc: psutil.Process, timeout: float) -> bool:
        """Wait for process to terminate within timeout seconds."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                    return True
            except psutil.NoSuchProcess:
                return True
            time.sleep(0.1)

        try:
            return not proc.is_running()
        except psutil.NoSuchProcess:
            return True

    def _is_port_freed(self, port: int, protocol: Protocol) -> bool:
        """Check if port is now available."""
        # Short sleep to allow OS kernel socket cleanup (TIME_WAIT, CLOSE_WAIT)
        time.sleep(0.1)
        port_info = self.scanner.scan_port(port, protocol)
        return port_info.status == PortStatus.AVAILABLE
