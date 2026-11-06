"""CLI argument parser and command dispatcher for PortPilot."""

import argparse
import sys

from portpilot import __version__
from portpilot.config import Config
from portpilot.docker_check import DockerComposeChecker
from portpilot.docker_compose import DockerComposeRunner
from portpilot.exceptions import (
    CriticalProcessError,
    PortPilotError,
    ProcessPermissionError,
)
from portpilot.formatter import OutputFormatter
from portpilot.logger import get_logger, setup_logger
from portpilot.models import Protocol
from portpilot.process_manager import ProcessManager
from portpilot.scanner import PortScanner
from portpilot.services import ServiceRegistry
from portpilot.utils import parse_port_range, parse_ports, validate_port

logger = get_logger()


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser with all commands and options."""
    # Shared options parser for global flags that can be specified before or after subcommand
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable informational logging output"
    )
    common_parser.add_argument(
        "--debug", action="store_true", help="Enable verbose debug logging output"
    )
    common_parser.add_argument(
        "--log-file", type=str, default=None, help="Path to write application log file"
    )
    common_parser.add_argument(
        "--no-color", action="store_true", help="Disable colored terminal output"
    )
    common_parser.add_argument(
        "--json", action="store_true", help="Output results in machine-readable JSON format"
    )
    common_parser.add_argument(
        "--config", type=str, default=None, help="Path to custom configuration file"
    )

    parser = argparse.ArgumentParser(
        prog="portpilot",
        description="PortPilot: Linux Port & Process Management CLI for Developers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command 1: check
    check_parser = subparsers.add_parser(
        "check",
        help="Scan local network ports for active listeners",
        parents=[common_parser],
    )
    check_group = check_parser.add_mutually_exclusive_group()
    check_group.add_argument(
        "--ports",
        type=str,
        help="Comma-separated list of ports (e.g. 5432,6379,8000)",
    )
    check_group.add_argument(
        "--range",
        type=str,
        help="Range of ports to scan (e.g. 3000-3010)",
    )
    check_group.add_argument(
        "--services",
        action="store_true",
        help="Scan all known development service ports",
    )
    check_parser.add_argument(
        "--protocol",
        choices=["tcp", "udp"],
        default="tcp",
        help="Transport protocol to inspect (default: tcp)",
    )

    # Command 2: services
    subparsers.add_parser(
        "services",
        help="List common development service port conventions",
        parents=[common_parser],
    )

    # Command 3: inspect
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Detailed process inspection for an occupied port",
        parents=[common_parser],
    )
    inspect_parser.add_argument("port", type=int, help="Port number to inspect")
    inspect_parser.add_argument(
        "--protocol",
        choices=["tcp", "udp"],
        default="tcp",
        help="Protocol to inspect (default: tcp)",
    )

    # Command 4: stop
    stop_parser = subparsers.add_parser(
        "stop",
        help="Safely terminate processes listening on a port",
        parents=[common_parser],
    )
    stop_parser.add_argument("port", type=int, help="Port number to free")
    stop_parser.add_argument(
        "--pid", type=int, default=None, help="Specific PID to terminate if multiple share port"
    )
    stop_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate termination without sending signals",
    )
    stop_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Grace period seconds to wait after SIGTERM (default from config: 5.0)",
    )
    stop_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Confirm termination non-interactively without prompt",
    )
    stop_parser.add_argument(
        "--sigkill",
        action="store_true",
        help="Send SIGKILL directly instead of SIGTERM",
    )
    stop_parser.add_argument(
        "--protocol",
        choices=["tcp", "udp"],
        default="tcp",
        help="Transport protocol (default: tcp)",
    )

    # Command 5: preflight
    preflight_parser = subparsers.add_parser(
        "preflight",
        help="Detect Docker Compose host port conflicts before container startup",
        parents=[common_parser],
    )
    preflight_parser.add_argument(
        "-f", "--file", type=str, default=None, help="Explicit path to Compose file"
    )

    # Command 6: compose
    compose_parser = subparsers.add_parser(
        "compose",
        help="Run Docker Compose commands with integrated conflict preflight check",
        parents=[common_parser],
    )
    compose_parser.add_argument(
        "-f", "--file", type=str, default=None, help="Explicit path to Compose file"
    )
    compose_parser.add_argument(
        "--force",
        action="store_true",
        help="Proceed with Compose execution even if port conflicts are found",
    )
    compose_parser.add_argument(
        "compose_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to docker compose (e.g. up -d, down)",
    )

    return parser


def run_cli(argv: list[str] | None = None) -> int:
    """Main CLI execution flow."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Setup logger
    setup_logger(
        verbose=args.verbose,
        debug=args.debug,
        log_file=args.log_file,
    )

    # Load configuration
    try:
        config = Config.load(args.config)
    except Exception as err:
        print(f"Configuration error: {err}", file=sys.stderr)
        return 1

    color_enabled = config.color and not args.no_color
    formatter = OutputFormatter(color_enabled=color_enabled)
    service_registry = ServiceRegistry(custom_presets=config.custom_services)
    scanner = PortScanner(service_registry=service_registry)

    # Default action if no subcommand is passed: check default ports
    cmd = args.command or "check"

    if not args.json and not args.no_color and cmd != "compose":
        # Show banner for interactive top-level commands
        formatter.print_banner()

    try:
        if cmd == "check":
            return handle_check(args, config, scanner, service_registry, formatter)
        elif cmd == "services":
            return handle_services(args, service_registry, formatter)
        elif cmd == "inspect":
            return handle_inspect(args, scanner, formatter)
        elif cmd == "stop":
            return handle_stop(args, config, scanner, formatter)
        elif cmd == "preflight":
            return handle_preflight(args, scanner, formatter)
        elif cmd == "compose":
            return handle_compose(args, scanner, formatter)
        else:
            parser.print_help()
            return 1
    except PortPilotError as err:
        print(formatter.colors.red(f"Error: {err}"), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
        return 130
    except Exception as err:
        logger.exception("Unexpected error occurred: %s", err)
        print(formatter.colors.red(f"Fatal error: {err}"), file=sys.stderr)
        return 1


def handle_check(
    args: argparse.Namespace,
    config: Config,
    scanner: PortScanner,
    service_registry: ServiceRegistry,
    formatter: OutputFormatter,
) -> int:
    """Handle 'check' command."""
    proto = Protocol.UDP if getattr(args, "protocol", "tcp") == "udp" else Protocol.TCP

    if getattr(args, "ports", None):
        ports = parse_ports(args.ports)
    elif getattr(args, "range", None):
        ports = parse_port_range(args.range)
    elif getattr(args, "services", False):
        ports = service_registry.get_all_ports(protocol=proto)
        if not ports:
            print("No services defined in registry for protocol.")
            return 0
    else:
        # Default ports from config
        ports = config.default_ports

    results = scanner.scan_ports(ports, protocol=proto)
    print(formatter.format_check_results(results, as_json=args.json))

    # Exit code: 0 if all ports available, 2 if any port is occupied
    has_occupied = any(r.status.value == "OCCUPIED" for r in results)
    return 2 if has_occupied else 0


def handle_services(
    args: argparse.Namespace,
    service_registry: ServiceRegistry,
    formatter: OutputFormatter,
) -> int:
    """Handle 'services' command."""
    presets = service_registry.get_all()
    print(formatter.format_services(presets, as_json=args.json))
    return 0


def handle_inspect(
    args: argparse.Namespace,
    scanner: PortScanner,
    formatter: OutputFormatter,
) -> int:
    """Handle 'inspect' command."""
    port = validate_port(args.port)
    proto = Protocol.UDP if getattr(args, "protocol", "tcp") == "udp" else Protocol.TCP

    port_info = scanner.scan_port(port, protocol=proto)
    print(formatter.format_inspect(port_info, as_json=args.json))
    return 0


def handle_stop(
    args: argparse.Namespace,
    config: Config,
    scanner: PortScanner,
    formatter: OutputFormatter,
) -> int:
    """Handle 'stop' command."""
    port = validate_port(args.port)
    proto = Protocol.UDP if getattr(args, "protocol", "tcp") == "udp" else Protocol.TCP
    timeout = args.timeout if args.timeout is not None else config.termination_timeout

    proc_mgr = ProcessManager(scanner=scanner)
    processes = proc_mgr.get_port_processes(port, protocol=proto)

    if not processes:
        print(f"No active process found listening on port {port}/{proto.value.upper()}.")
        return 0

    target_pid = args.pid
    target_procs = processes
    if target_pid is not None:
        target_procs = [p for p in processes if p.pid == target_pid]
        if not target_procs:
            print(
                formatter.colors.red(
                    f"PID {target_pid} is not among the processes occupying port {port}."
                ),
                file=sys.stderr,
            )
            return 1

    # Perform safety validation and display process details
    exit_code = 0
    for target in target_procs:
        try:
            proc_mgr.validate_target_process(target)
        except CriticalProcessError as err:
            print(formatter.colors.red(f"Safety restriction: {err}"), file=sys.stderr)
            return 1
        except ProcessPermissionError as err:
            print(formatter.colors.red(f"Permission error: {err}"), file=sys.stderr)
            return 1

        warnings = proc_mgr.check_safety_warnings(target)
        if warnings:
            print(formatter.colors.yellow("\nSAFETY WARNINGS:"))
            for w in warnings:
                print(formatter.colors.yellow(f"  [!] {w}"))
            print()

        # Display target process details
        print(formatter.colors.bold(f"Target process for termination (Port {port}):"))
        print(f"  PID:        {target.pid}")
        print(f"  Name:       {target.name}")
        print(f"  User:       {target.username or 'unknown'}")
        print(f"  Command:    {' '.join(target.cmdline) if target.cmdline else target.name}")
        print()

        # Require explicit confirmation unless --yes or --dry-run
        if not args.yes and not args.dry_run:
            prompt_sig = "SIGKILL" if args.sigkill else "SIGTERM"
            try:
                answer = (
                    input(
                        f"Send {prompt_sig} to terminate process {target.pid} ({target.name})? [y/N]: "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                print("\nOperation cancelled.")
                return 130

            if answer not in ("y", "yes"):
                print("Termination cancelled by user.")
                return 0

        # Terminate
        result = proc_mgr.terminate_process(
            port=port,
            proc_info=target,
            timeout=timeout,
            dry_run=args.dry_run,
            use_sigkill=args.sigkill,
            protocol=proto,
        )

        # If SIGTERM timed out and interactive, offer SIGKILL escalation
        if (
            not result.success
            and not args.sigkill
            and not args.dry_run
            and not args.yes
            and sys.stdin.isatty()
        ):
            print(formatter.colors.yellow(result.message))
            try:
                escalate = (
                    input(
                        f"Would you like to escalate and force terminate (SIGKILL) PID {target.pid}? [y/N]: "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                print("\nEscalation cancelled.")
                return 130

            if escalate in ("y", "yes"):
                result = proc_mgr.terminate_process(
                    port=port,
                    proc_info=target,
                    timeout=2.0,
                    dry_run=False,
                    use_sigkill=True,
                    protocol=proto,
                )

        print(formatter.format_stop_result(result, as_json=args.json))
        if not result.success:
            exit_code = 1

    return exit_code


def handle_preflight(
    args: argparse.Namespace,
    scanner: PortScanner,
    formatter: OutputFormatter,
) -> int:
    """Handle 'preflight' command."""
    checker = DockerComposeChecker(scanner=scanner)
    result = checker.run_preflight(args.file)
    print(formatter.format_preflight(result, as_json=args.json))
    return 1 if result.has_conflicts else 0


def handle_compose(
    args: argparse.Namespace,
    scanner: PortScanner,
    formatter: OutputFormatter,
) -> int:
    """Handle 'compose' command."""
    compose_args = args.compose_args
    if not compose_args:
        print("Usage: portpilot compose <command> (e.g. up, down, ps)", file=sys.stderr)
        return 1

    checker = DockerComposeChecker(scanner=scanner)
    runner = DockerComposeRunner(checker=checker, formatter=formatter)
    return runner.run_compose_command(
        command_args=compose_args,
        compose_file=args.file,
        force=args.force,
    )
