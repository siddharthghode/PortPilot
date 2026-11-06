"""CLI execution entrypoint for PortPilot."""

import sys

from portpilot.cli import run_cli


def main() -> None:
    """Execute PortPilot CLI and exit with appropriate process exit code."""
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
