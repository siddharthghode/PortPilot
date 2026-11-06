"""Docker Compose command execution wrapper with preflight guard."""

import shutil
import subprocess
import sys
from pathlib import Path

from portpilot.docker_check import DockerComposeChecker
from portpilot.exceptions import ComposeError
from portpilot.formatter import OutputFormatter
from portpilot.logger import get_logger

logger = get_logger()


class DockerComposeRunner:
    """Safely executes Docker Compose commands with preflight validation."""

    def __init__(
        self,
        checker: DockerComposeChecker | None = None,
        formatter: OutputFormatter | None = None,
    ) -> None:
        self.checker = checker or DockerComposeChecker()
        self.formatter = formatter or OutputFormatter()

    @staticmethod
    def get_compose_command_prefix() -> list[str]:
        """Detect whether 'docker compose' (v2 plugin) or 'docker-compose' (v1) is available."""
        # Check docker compose v2 plugin
        if shutil.which("docker"):
            try:
                res = subprocess.run(
                    ["docker", "compose", "version"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0:
                    return ["docker", "compose"]
            except Exception:
                pass

        # Fallback to docker-compose v1
        if shutil.which("docker-compose"):
            return ["docker-compose"]

        raise ComposeError(
            "Neither 'docker compose' (v2) nor 'docker-compose' (v1) was found on PATH."
        )

    def run_compose_command(
        self,
        command_args: list[str],
        compose_file: str | Path | None = None,
        force: bool = False,
    ) -> int:
        """Run a Docker Compose command (e.g. ['up', '-d']), running preflight if 'up' is used.

        Args:
            command_args: Arguments passed to compose (e.g. ['up', '-d']).
            compose_file: Optional explicit path to compose file.
            force: Proceed even if conflicts are detected.

        Returns:
            Subprocess exit code.
        """
        is_up_command = "up" in command_args

        if is_up_command:
            logger.info("Running preflight check before docker compose up...")
            try:
                preflight_result = self.checker.run_preflight(compose_file)
            except ComposeError as err:
                print(self.formatter.colors.red(f"Preflight error: {err}"), file=sys.stderr)
                return 1

            if preflight_result.has_conflicts:
                print(self.formatter.format_preflight(preflight_result))
                print()
                if not force:
                    print(
                        self.formatter.colors.red(
                            "Docker Compose startup aborted due to host port conflicts.\n"
                            "Use 'portpilot inspect <port>' to examine conflicts, or 'portpilot stop <port>' to resolve.\n"
                            "To bypass preflight and proceed anyway, re-run with --force."
                        ),
                        file=sys.stderr,
                    )
                    return 1
                else:
                    print(
                        self.formatter.colors.yellow(
                            "Proceeding with Docker Compose execution despite detected conflicts (--force specified)..."
                        )
                    )
            else:
                print(self.formatter.format_preflight(preflight_result))

        prefix = self.get_compose_command_prefix()
        full_cmd = list(prefix)

        if compose_file:
            full_cmd.extend(["-f", str(compose_file)])

        full_cmd.extend(command_args)

        logger.info("Executing: %s", " ".join(full_cmd))
        try:
            # Run without shell=True, streaming output directly to user terminal
            proc = subprocess.run(full_cmd, check=False)
            return proc.returncode
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return 130
        except Exception as err:
            logger.error("Failed to execute Docker Compose: %s", err)
            return 1
