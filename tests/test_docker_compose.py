"""Unit tests for DockerComposeRunner."""

from unittest.mock import MagicMock, patch

import pytest

from portpilot.docker_compose import DockerComposeRunner
from portpilot.exceptions import ComposeError
from portpilot.models import (
    ComposePreflightConflict,
    ComposePreflightResult,
    PortInfo,
    PortStatus,
    ProcessInfo,
    Protocol,
)


def test_get_compose_command_prefix_v2():
    with patch("shutil.which", return_value="/usr/bin/docker"), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        prefix = DockerComposeRunner.get_compose_command_prefix()
        assert prefix == ["docker", "compose"]


def test_get_compose_command_prefix_v1():
    def fake_which(cmd):
        if cmd == "docker":
            return None
        if cmd == "docker-compose":
            return "/usr/bin/docker-compose"
        return None

    with patch("shutil.which", side_effect=fake_which):
        prefix = DockerComposeRunner.get_compose_command_prefix()
        assert prefix == ["docker-compose"]


def test_get_compose_command_prefix_not_found():
    with patch("shutil.which", return_value=None):
        with pytest.raises(ComposeError, match="Neither 'docker compose'"):
            DockerComposeRunner.get_compose_command_prefix()


def test_run_compose_command_up_clean_success():
    mock_checker = MagicMock()
    mock_checker.run_preflight.return_value = ComposePreflightResult(
        compose_file="docker-compose.yml",
        mappings=[],
        conflicts=[],
        warnings=[],
    )

    runner = DockerComposeRunner(checker=mock_checker)

    with (
        patch.object(runner, "get_compose_command_prefix", return_value=["docker", "compose"]),
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run,
    ):
        code = runner.run_compose_command(["up", "-d"], compose_file="docker-compose.yml")
        assert code == 0
        mock_run.assert_called_once_with(
            ["docker", "compose", "-f", "docker-compose.yml", "up", "-d"],
            check=False,
        )


def test_run_compose_command_up_conflicts_aborts():
    mock_checker = MagicMock()
    conflict = ComposePreflightConflict(
        service_name="web",
        host_port=80,
        host_ip="0.0.0.0",
        protocol=Protocol.TCP,
        port_info=PortInfo(
            port=80,
            protocol=Protocol.TCP,
            status=PortStatus.OCCUPIED,
            processes=[ProcessInfo(pid=123, name="nginx")],
        ),
    )
    mock_checker.run_preflight.return_value = ComposePreflightResult(
        compose_file="docker-compose.yml",
        mappings=[],
        conflicts=[conflict],
        warnings=[],
    )

    runner = DockerComposeRunner(checker=mock_checker)
    code = runner.run_compose_command(["up", "-d"], force=False)
    # Aborts with code 1
    assert code == 1


def test_run_compose_command_up_conflicts_forced():
    mock_checker = MagicMock()
    conflict = ComposePreflightConflict(
        service_name="web",
        host_port=80,
        host_ip="0.0.0.0",
        protocol=Protocol.TCP,
        port_info=PortInfo(
            port=80,
            protocol=Protocol.TCP,
            status=PortStatus.OCCUPIED,
            processes=[ProcessInfo(pid=123, name="nginx")],
        ),
    )
    mock_checker.run_preflight.return_value = ComposePreflightResult(
        compose_file="docker-compose.yml",
        mappings=[],
        conflicts=[conflict],
        warnings=[],
    )

    runner = DockerComposeRunner(checker=mock_checker)

    with (
        patch.object(runner, "get_compose_command_prefix", return_value=["docker", "compose"]),
        patch("subprocess.run", return_value=MagicMock(returncode=0)),
    ):
        code = runner.run_compose_command(["up", "-d"], force=True)
        assert code == 0


def test_run_compose_command_non_up_bypasses_preflight():
    mock_checker = MagicMock()
    runner = DockerComposeRunner(checker=mock_checker)

    with (
        patch.object(runner, "get_compose_command_prefix", return_value=["docker", "compose"]),
        patch("subprocess.run", return_value=MagicMock(returncode=0)),
    ):
        code = runner.run_compose_command(["down"])
        assert code == 0
        mock_checker.run_preflight.assert_not_called()


def test_run_compose_command_interrupt():
    mock_checker = MagicMock()
    runner = DockerComposeRunner(checker=mock_checker)

    with (
        patch.object(runner, "get_compose_command_prefix", return_value=["docker", "compose"]),
        patch("subprocess.run", side_effect=KeyboardInterrupt),
    ):
        code = runner.run_compose_command(["down"])
        assert code == 130
