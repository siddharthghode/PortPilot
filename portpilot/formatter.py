"""Terminal output formatting and JSON serializers for PortPilot."""

import json
import re

from portpilot.inspector import ProcessInspector
from portpilot.models import (
    ComposePreflightResult,
    PortInfo,
    PortStatus,
    ServicePreset,
    StopResult,
)
from portpilot.services import CONVENTION_DISCLAIMER
from portpilot.utils import Colorizer

APP_BANNER = """
═════════════════════════════════════════════════════════════════
  PORTPILOT — Linux Port & Process Management CLI
═════════════════════════════════════════════════════════════════
"""

ANSI_PATTERN = re.compile(r"\033\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from string."""
    return ANSI_PATTERN.sub("", text)


def pad_ansi(text: str, width: int, align: str = "left") -> str:
    """Pad string to visible terminal column width, ignoring ANSI escape characters."""
    visible_len = len(strip_ansi(text))
    padding = max(0, width - visible_len)
    if align == "right":
        return (" " * padding) + text
    return text + (" " * padding)


class OutputFormatter:
    """Formats PortPilot entities for human-readable terminal display or JSON export."""

    def __init__(self, color_enabled: bool = True) -> None:
        self.colors = Colorizer(enabled=color_enabled)

    def print_banner(self) -> None:
        """Display ASCII header."""
        print(self.colors.cyan(APP_BANNER.strip()))
        print()

    # --- PORT CHECK FORMATTING ---

    def format_check_results(self, results: list[PortInfo], as_json: bool = False) -> str:
        """Format port scanning results."""
        if as_json:
            return json.dumps([r.to_dict() for r in results], indent=2)

        lines: list[str] = []
        occupied_count = sum(1 for r in results if r.status == PortStatus.OCCUPIED)

        # Header
        lines.append(
            self.colors.bold(
                f"{'STATUS':<8} {'PORT':<7} {'PROTO':<6} {'SERVICE':<16} {'PID':<8} {'PROCESS':<18} {'ADDRESS':<16}"
            )
        )
        lines.append("-" * 83)

        for r in results:
            if r.status == PortStatus.OCCUPIED:
                badge = self.colors.fail_badge()
            elif r.status == PortStatus.AVAILABLE:
                badge = self.colors.pass_badge()
            else:
                badge = self.colors.warn_badge()

            badge_str = pad_ansi(badge, 8)
            port_str = pad_ansi(str(r.port), 7)
            proto_str = pad_ansi(r.protocol.value.upper(), 6)

            service_str = ", ".join(r.services) if r.services else "-"
            if len(service_str) > 15:
                service_str = service_str[:12] + "..."
            service_str = pad_ansi(service_str, 16)

            if r.processes:
                for idx, p in enumerate(r.processes):
                    pid_str = pad_ansi(str(p.pid) if p.pid else "-", 8)
                    proc_name = p.name or "unknown"
                    if len(proc_name) > 17:
                        proc_name = proc_name[:14] + "..."
                    proc_name = pad_ansi(proc_name, 18)
                    addr_str = r.local_address or "-"
                    if len(addr_str) > 15:
                        addr_str = addr_str[:12] + "..."
                    addr_str = pad_ansi(addr_str, 16)

                    if idx == 0:
                        lines.append(
                            f"{badge_str} {port_str} {proto_str} {service_str} {pid_str} {proc_name} {addr_str}"
                        )
                    else:
                        lines.append(
                            f"{pad_ansi('', 8)} {pad_ansi('', 7)} {pad_ansi('', 6)} {pad_ansi('', 16)} {pid_str} {proc_name} {addr_str}"
                        )
            else:
                addr_str = r.local_address or "-"
                lines.append(
                    f"{badge_str} {port_str} {proto_str} {service_str} {pad_ansi('-', 8)} {pad_ansi('-', 18)} {pad_ansi(addr_str, 16)}"
                )

        lines.append("-" * 83)
        if occupied_count > 0:
            lines.append(
                self.colors.yellow(
                    f"Found {occupied_count} occupied port{'s' if occupied_count > 1 else ''} out of {len(results)} checked."
                )
            )
        else:
            lines.append(
                self.colors.green(f"All {len(results)} ports available. No conflicts detected.")
            )

        return "\n".join(lines)

    # --- SERVICE PRESETS FORMATTING ---

    def format_services(self, presets: list[ServicePreset], as_json: bool = False) -> str:
        """Format known service presets table."""
        if as_json:
            return json.dumps([p.to_dict() for p in presets], indent=2)

        lines: list[str] = []
        lines.append(
            self.colors.bold(
                f"{'PORT':<7} {'PROTOCOL':<10} {'SERVICE NAME':<22} {'CATEGORY':<16} {'DESCRIPTION'}"
            )
        )
        lines.append("-" * 85)

        for p in presets:
            lines.append(
                f"{p.port:<7} {p.protocol.value.upper():<10} {self.colors.cyan(p.name):<22} {p.category:<16} {p.description}"
            )

        lines.append("-" * 85)
        lines.append(self.colors.gray(CONVENTION_DISCLAIMER))
        return "\n".join(lines)

    # --- PROCESS INSPECT FORMATTING ---

    def format_inspect(self, port_info: PortInfo, as_json: bool = False) -> str:
        """Format detailed process inspection report for a port."""
        if as_json:
            return json.dumps(port_info.to_dict(), indent=2)

        lines: list[str] = []
        lines.append(
            self.colors.bold(
                f"PORT INSPECTION: {port_info.port}/{port_info.protocol.value.upper()}"
            )
        )
        lines.append("=" * 60)
        lines.append(f"  Port:          {port_info.port}")
        lines.append(f"  Protocol:      {port_info.protocol.value.upper()}")
        lines.append(
            f"  Status:        {self.colors.red('OCCUPIED') if port_info.status == PortStatus.OCCUPIED else self.colors.green('AVAILABLE')}"
        )
        lines.append(f"  Local Address: {port_info.local_address or 'None'}")
        if port_info.services:
            lines.append(f"  Known Service: {', '.join(port_info.services)} (convention)")

        if not port_info.processes:
            if port_info.status == PortStatus.OCCUPIED:
                lines.append(
                    self.colors.yellow(
                        "  Processes:     No PID identifiable (run with elevated privileges)"
                    )
                )
            else:
                lines.append("  Processes:     None (port is unoccupied)")
            return "\n".join(lines)

        lines.append("\n" + self.colors.bold("OCCUPYING PROCESSES:"))
        for idx, p in enumerate(port_info.processes, start=1):
            lines.append(f"  [{idx}] PID {self.colors.bold(str(p.pid))}:")
            lines.append(f"      Process Name:     {self.colors.cyan(p.name)}")
            lines.append(f"      Status:           {p.status or 'unknown'}")
            lines.append(f"      Parent PID (PPID):{p.ppid if p.ppid is not None else 'unknown'}")
            lines.append(f"      User:             {p.username or 'unknown'}")
            lines.append(f"      Executable:       {p.exe or 'unknown'}")
            cmdline_str = " ".join(p.cmdline) if p.cmdline else "unknown"
            if len(cmdline_str) > 80:
                cmdline_str = cmdline_str[:77] + "..."
            lines.append(f"      Command Line:     {cmdline_str}")
            lines.append(
                f"      Start Time:       {ProcessInspector.format_start_time(p.create_time)}"
            )

            # Systemd & Docker hints
            if p.is_systemd:
                lines.append(
                    self.colors.yellow(
                        f"      Systemd Service:  YES ({p.systemd_service or 'active unit'})"
                    )
                )
            else:
                lines.append("      Systemd Service:  No")

            if p.is_docker:
                lines.append(
                    self.colors.blue(
                        f"      Docker Managed:   YES ({p.docker_container_id or 'container process'})"
                    )
                )
            else:
                lines.append("      Docker Managed:   No")

        return "\n".join(lines)

    # --- DOCKER PREFLIGHT FORMATTING ---

    def format_preflight(self, result: ComposePreflightResult, as_json: bool = False) -> str:
        """Format Docker Compose preflight check results."""
        if as_json:
            return json.dumps(result.to_dict(), indent=2)

        lines: list[str] = []
        lines.append(self.colors.bold("PORTPILOT DOCKER PREFLIGHT"))
        lines.append(f"Compose file: {result.compose_file}")
        lines.append("=" * 68)
        lines.append(
            f"{'SERVICE':<16} {'HOST PORT':<12} {'PROTOCOL':<10} {'STATUS':<12} {'DETAILS'}"
        )
        lines.append("-" * 68)

        conflict_ports = {c.host_port for c in result.conflicts}

        for m in result.mappings:
            is_conflicted = m.host_port in conflict_ports
            if is_conflicted:
                status_str = self.colors.fail_badge()
                conf = next((c for c in result.conflicts if c.host_port == m.host_port), None)
                details = "Conflict with host process"
                if conf and conf.port_info.processes:
                    proc = conf.port_info.processes[0]
                    details = f"PID {proc.pid} ({proc.name})"
            else:
                status_str = self.colors.pass_badge()
                details = "Ready to bind"

            host_port_display = f"{m.host_ip + ':' if m.host_ip else ''}{m.host_port}"
            lines.append(
                f"{pad_ansi(m.service_name, 16)} {pad_ansi(host_port_display, 12)} {pad_ansi(m.protocol.value.upper(), 10)} {pad_ansi(status_str, 12)} {details}"
            )

        lines.append("-" * 68)

        if result.warnings:
            lines.append(self.colors.bold("WARNINGS:"))
            for w in result.warnings:
                lines.append(self.colors.yellow(f"  • {w}"))
            lines.append("-" * 68)

        if result.has_conflicts:
            count = len(result.conflicts)
            lines.append(
                self.colors.red(
                    f"{count} conflict{'s' if count > 1 else ''} detected! Container startup will fail without resolution."
                )
            )
        else:
            lines.append(self.colors.green("All Compose host ports are available. Safe to launch!"))

        return "\n".join(lines)

    # --- STOP RESULT FORMATTING ---

    def format_stop_result(self, result: StopResult, as_json: bool = False) -> str:
        """Format process termination result."""
        if as_json:
            return json.dumps(result.to_dict(), indent=2)

        lines: list[str] = []
        if result.dry_run:
            lines.append(self.colors.yellow("[DRY RUN] No processes were terminated."))
            lines.append(f"Target PID:     {result.pid} ({result.process_name})")
            lines.append(f"Target Port:    {result.port}")
            lines.append(f"Action:         {result.message}")
            return "\n".join(lines)

        if result.success:
            lines.append(self.colors.green(f"[SUCCESS] {result.message}"))
            if result.port_freed:
                lines.append(self.colors.green(f"Verified: Port {result.port} is now AVAILABLE."))
            else:
                lines.append(
                    self.colors.yellow(
                        f"Warning: Port {result.port} remains occupied by another process."
                    )
                )
        else:
            lines.append(self.colors.red(f"[FAILURE] {result.message}"))

        return "\n".join(lines)
