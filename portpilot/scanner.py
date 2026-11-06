"""Port scanner for local TCP and UDP sockets using psutil and ss fallback."""

import re
import subprocess
from collections import defaultdict
from typing import Any

import psutil

from portpilot.inspector import ProcessInspector
from portpilot.logger import get_logger
from portpilot.models import PortInfo, PortStatus, ProcessInfo, Protocol
from portpilot.services import ServiceRegistry
from portpilot.utils import validate_port

logger = get_logger()


class PortScanner:
    """Detects occupied network ports and their associated processes."""

    def __init__(self, service_registry: ServiceRegistry | None = None) -> None:
        self.service_registry = service_registry or ServiceRegistry()
        self.inspector = ProcessInspector()

    def scan_port(self, port: int, protocol: Protocol = Protocol.TCP) -> PortInfo:
        """Scan a single port for the given protocol."""
        results = self.scan_ports([port], protocol=protocol)
        return results[0]

    def scan_ports(self, ports: list[int], protocol: Protocol = Protocol.TCP) -> list[PortInfo]:
        """Scan a list of ports for the given protocol."""
        for p in ports:
            validate_port(p)

        # Retrieve all system listening/bound connections indexed by port
        connections_by_port, global_error = self._get_active_sockets(protocol)

        results: list[PortInfo] = []
        for port in ports:
            matched = connections_by_port.get(port, [])
            services = self.service_registry.get_service_names_for_port(port, protocol)

            if matched:
                # Port is occupied
                addresses = set()
                processes: list[ProcessInfo] = []
                seen_pids = set()

                for entry in matched:
                    laddr = entry.get("laddr")
                    if laddr:
                        addresses.add(laddr)
                    pid = entry.get("pid")
                    if pid:
                        if pid not in seen_pids:
                            seen_pids.add(pid)
                            proc_info = self.inspector.inspect_pid(pid)
                            processes.append(proc_info)
                    else:
                        # Process ID hidden by OS permissions
                        if 0 not in seen_pids:
                            seen_pids.add(0)
                            processes.append(
                                ProcessInfo(
                                    pid=0,
                                    name="<access-restricted>",
                                    username="<elevated/system>",
                                    status="restricted",
                                )
                            )

                local_addr_str = ", ".join(sorted(addresses)) if addresses else "unknown"
                results.append(
                    PortInfo(
                        port=port,
                        protocol=protocol,
                        status=PortStatus.OCCUPIED,
                        local_address=local_addr_str,
                        processes=processes,
                        services=services,
                    )
                )
            else:
                # Port is available or permission error
                status = PortStatus.AVAILABLE
                error = None
                if global_error:
                    status = PortStatus.PERMISSION_DENIED
                    error = global_error

                results.append(
                    PortInfo(
                        port=port,
                        protocol=protocol,
                        status=status,
                        local_address=None,
                        processes=[],
                        services=services,
                        error=error,
                    )
                )

        return results

    def _get_active_sockets(
        self, protocol: Protocol
    ) -> tuple[dict[int, list[dict[str, Any]]], str | None]:
        """Retrieve active local sockets from psutil with fallback to Linux ss command."""
        connections_by_port: dict[int, list[dict[str, Any]]] = defaultdict(list)
        error: str | None = None

        psutil_worked = False
        try:
            kind = "tcp" if protocol == Protocol.TCP else "udp"
            conns = psutil.net_connections(kind=kind)
            psutil_worked = True

            for conn in conns:
                # Check socket status
                is_target = False
                if protocol == Protocol.TCP:
                    # TCP sockets in LISTEN state
                    if conn.status == psutil.CONN_LISTEN:
                        is_target = True
                elif protocol == Protocol.UDP:
                    # UDP sockets bound locally (connectionless or unconn)
                    if conn.status in (psutil.CONN_NONE, "") or not conn.raddr:
                        is_target = True

                if is_target and conn.laddr:
                    port = conn.laddr.port
                    connections_by_port[port].append(
                        {
                            "laddr": f"{conn.laddr.ip}:{conn.laddr.port}",
                            "ip": conn.laddr.ip,
                            "port": conn.laddr.port,
                            "pid": conn.pid,
                            "status": conn.status,
                            "protocol": protocol,
                        }
                    )
        except (psutil.AccessDenied, PermissionError) as err:
            logger.warning("psutil.net_connections AccessDenied: %s. Falling back to ss.", err)
            error = "Access denied: elevated privileges required for complete inspection."
        except Exception as err:
            logger.debug("psutil.net_connections error: %s. Trying ss.", err)

        # If psutil failed or returned no listening ports, or if PIDs were missing,
        # augment / fallback with `ss` command
        ss_conns = self._get_sockets_from_ss(protocol)
        if not psutil_worked and ss_conns:
            return ss_conns, None

        # Augment missing PIDs from ss if psutil had pid=None
        if ss_conns:
            for port, ss_entries in ss_conns.items():
                if port not in connections_by_port:
                    connections_by_port[port].extend(ss_entries)
                else:
                    # Supplement PID info if psutil missed it
                    existing_entries = connections_by_port[port]
                    for entry in existing_entries:
                        if entry.get("pid") is None:
                            for ss_entry in ss_entries:
                                if ss_entry.get("pid"):
                                    entry["pid"] = ss_entry["pid"]
                                    break

        return connections_by_port, error

    def _get_sockets_from_ss(self, protocol: Protocol) -> dict[int, list[dict[str, Any]]]:
        """Execute and parse Linux `ss` command to inspect listening sockets."""
        connections_by_port: dict[int, list[dict[str, Any]]] = defaultdict(list)
        flag = "-tlnp" if protocol == Protocol.TCP else "-ulnp"

        try:
            cmd = ["ss", flag]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if proc.returncode != 0:
                logger.debug("ss command failed with returncode %d", proc.returncode)
                return connections_by_port

            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("Netid") or line.startswith("State"):
                    continue

                parts = line.split()
                if len(parts) < 4:
                    continue

                # In ss output:
                # State Recv-Q Send-Q Local Address:Port Peer Address:Port Process
                # or: Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port Process
                local_addr = None
                process_field = None

                for idx, col in enumerate(parts):
                    if ":" in col and not col.startswith("users:"):
                        local_addr = col
                        # Process field is typically the last column
                        if len(parts) > idx + 2:
                            process_field = " ".join(parts[idx + 2 :])
                        break

                if not local_addr:
                    continue

                ip, port = self._parse_ss_address(local_addr)
                if port is None:
                    continue

                pids = self._parse_ss_pids(process_field) if process_field else []
                if not pids:
                    connections_by_port[port].append(
                        {
                            "laddr": local_addr,
                            "ip": ip,
                            "port": port,
                            "pid": None,
                            "status": "LISTEN" if protocol == Protocol.TCP else "UNCONN",
                            "protocol": protocol,
                        }
                    )
                else:
                    for pid in pids:
                        connections_by_port[port].append(
                            {
                                "laddr": local_addr,
                                "ip": ip,
                                "port": port,
                                "pid": pid,
                                "status": "LISTEN" if protocol == Protocol.TCP else "UNCONN",
                                "protocol": protocol,
                            }
                        )

        except Exception as err:
            logger.debug("Failed running ss fallback: %s", err)

        return connections_by_port

    @staticmethod
    def _parse_ss_address(addr_str: str) -> tuple[str, int | None]:
        """Parse address string like '127.0.0.1:8000', '*:80', or '[::]:443'."""
        try:
            if addr_str.startswith("["):
                # IPv6 format [::1]:80 or [::]:80
                parts = addr_str.rsplit("]:", 1)
                ip = parts[0].lstrip("[")
                port_str = parts[1]
            else:
                parts = addr_str.rsplit(":", 1)
                ip = parts[0]
                port_str = parts[1]

            if port_str == "*":
                return ip, None
            return ip, int(port_str)
        except (ValueError, IndexError):
            return addr_str, None

    @staticmethod
    def _parse_ss_pids(process_field: str) -> list[int]:
        """Extract PIDs from ss process column: users:(("postgres",pid=1234,fd=5))."""
        pids: list[int] = []
        matches = re.findall(r"pid=(\d+)", process_field)
        for m in matches:
            try:
                pids.append(int(m))
            except ValueError:
                pass
        return pids
