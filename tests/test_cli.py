"""Unit and integration tests for the CLI entry point."""

from pathlib import Path
from unittest.mock import patch

import pytest

from portpilot.cli import build_parser, run_cli
from portpilot.models import PortInfo, PortStatus, ProcessInfo, Protocol, StopResult


def test_build_parser_help():
    parser = build_parser()
    assert parser.prog == "portpilot"


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "portpilot" in captured.out


def test_cli_check_ports_available(capsys):
    mock_info = PortInfo(
        port=5432,
        protocol=Protocol.TCP,
        status=PortStatus.AVAILABLE,
    )
    with patch("portpilot.scanner.PortScanner.scan_ports", return_value=[mock_info]):
        code = run_cli(["check", "--ports", "5432", "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "5432" in captured.out
        assert "[PASS]" in captured.out


def test_cli_check_ports_occupied(capsys):
    mock_info = PortInfo(
        port=5432,
        protocol=Protocol.TCP,
        status=PortStatus.OCCUPIED,
        local_address="127.0.0.1:5432",
        processes=[ProcessInfo(pid=1234, name="postgres")],
    )
    with patch("portpilot.scanner.PortScanner.scan_ports", return_value=[mock_info]):
        code = run_cli(["check", "--ports", "5432", "--no-color"])
        assert code == 2  # Occupied returns exit code 2
        captured = capsys.readouterr()
        assert "[FAIL]" in captured.out
        assert "1234" in captured.out


def test_cli_check_json_output(capsys):
    mock_info = PortInfo(
        port=6379,
        protocol=Protocol.TCP,
        status=PortStatus.AVAILABLE,
    )
    with patch("portpilot.scanner.PortScanner.scan_ports", return_value=[mock_info]):
        code = run_cli(["check", "--ports", "6379", "--json"])
        assert code == 0
        captured = capsys.readouterr()
        # Verify valid JSON
        import json

        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert data[0]["port"] == 6379
        assert data[0]["status"] == "AVAILABLE"


def test_cli_services(capsys):
    code = run_cli(["services", "--no-color"])
    assert code == 0
    captured = capsys.readouterr()
    assert "PostgreSQL" in captured.out
    assert "Redis" in captured.out


def test_cli_inspect_occupied(capsys):
    mock_info = PortInfo(
        port=8000,
        protocol=Protocol.TCP,
        status=PortStatus.OCCUPIED,
        local_address="0.0.0.0:8000",
        processes=[
            ProcessInfo(
                pid=9999,
                name="uvicorn",
                username="developer",
                cmdline=["uvicorn", "main:app"],
                status="running",
            )
        ],
    )
    with patch("portpilot.scanner.PortScanner.scan_port", return_value=mock_info):
        code = run_cli(["inspect", "8000", "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "PORT INSPECTION: 8000/TCP" in captured.out
        assert "uvicorn" in captured.out
        assert "9999" in captured.out


def test_cli_stop_dry_run(capsys):
    target = ProcessInfo(pid=8888, name="django-server")
    with (
        patch("portpilot.process_manager.ProcessManager.get_port_processes", return_value=[target]),
        patch("portpilot.process_manager.ProcessManager.validate_target_process"),
        patch("portpilot.process_manager.ProcessManager.check_safety_warnings", return_value=[]),
    ):
        code = run_cli(["stop", "8000", "--dry-run", "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "8888" in captured.out


def test_cli_stop_confirmed(capsys):
    target = ProcessInfo(pid=8888, name="django-server")
    mock_result = StopResult(
        port=8000,
        pid=8888,
        process_name="django-server",
        signal_sent="SIGTERM",
        success=True,
        port_freed=True,
        message="Terminated successfully",
    )
    with (
        patch("portpilot.process_manager.ProcessManager.get_port_processes", return_value=[target]),
        patch("portpilot.process_manager.ProcessManager.validate_target_process"),
        patch("portpilot.process_manager.ProcessManager.check_safety_warnings", return_value=[]),
        patch(
            "portpilot.process_manager.ProcessManager.terminate_process", return_value=mock_result
        ),
    ):
        code = run_cli(["stop", "8000", "--yes", "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "[SUCCESS]" in captured.out


def test_cli_preflight(tmp_compose_file: Path, capsys):
    mock_info = PortInfo(port=8080, protocol=Protocol.TCP, status=PortStatus.AVAILABLE)
    with patch("portpilot.scanner.PortScanner.scan_ports", return_value=[mock_info]):
        code = run_cli(["preflight", "-f", str(tmp_compose_file), "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "PORTPILOT DOCKER PREFLIGHT" in captured.out


def test_cli_check_range(capsys):
    mock_info = PortInfo(port=3000, protocol=Protocol.TCP, status=PortStatus.AVAILABLE)
    with patch("portpilot.scanner.PortScanner.scan_ports", return_value=[mock_info]):
        code = run_cli(["check", "--range", "3000-3002", "--no-color"])
        assert code == 0


def test_cli_check_services_flag(capsys):
    mock_info = PortInfo(port=5432, protocol=Protocol.TCP, status=PortStatus.AVAILABLE)
    with patch("portpilot.scanner.PortScanner.scan_ports", return_value=[mock_info]):
        code = run_cli(["check", "--services", "--no-color"])
        assert code == 0


def test_cli_stop_cancelled_by_user(capsys):
    target = ProcessInfo(pid=8888, name="django-server")
    with (
        patch("portpilot.process_manager.ProcessManager.get_port_processes", return_value=[target]),
        patch("portpilot.process_manager.ProcessManager.validate_target_process"),
        patch("portpilot.process_manager.ProcessManager.check_safety_warnings", return_value=[]),
        patch("builtins.input", return_value="n"),
    ):
        code = run_cli(["stop", "8000", "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "cancelled by user" in captured.out


def test_cli_stop_specific_pid_not_found(capsys):
    target = ProcessInfo(pid=8888, name="django-server")
    with patch(
        "portpilot.process_manager.ProcessManager.get_port_processes", return_value=[target]
    ):
        code = run_cli(["stop", "8000", "--pid", "9999", "--no-color"])
        assert code == 1
        captured = capsys.readouterr()
        assert "PID 9999 is not among" in captured.err


def test_cli_stop_no_process_listening(capsys):
    with patch("portpilot.process_manager.ProcessManager.get_port_processes", return_value=[]):
        code = run_cli(["stop", "9999", "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "No active process found" in captured.out


def test_cli_compose_command(capsys):
    with patch("portpilot.docker_compose.DockerComposeRunner.run_compose_command", return_value=0):
        code = run_cli(["compose", "down", "--no-color"])
        assert code == 0


def test_cli_compose_empty_args(capsys):
    code = run_cli(["compose"])
    assert code == 1


def test_cli_inspect_udp(capsys):
    mock_info = PortInfo(port=53, protocol=Protocol.UDP, status=PortStatus.AVAILABLE)
    with patch("portpilot.scanner.PortScanner.scan_port", return_value=mock_info):
        code = run_cli(["inspect", "53", "--protocol", "udp", "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "53/UDP" in captured.out


def test_cli_stop_sigkill_flag(capsys):
    target = ProcessInfo(pid=7777, name="stuck-worker")
    mock_result = StopResult(
        port=8000,
        pid=7777,
        process_name="stuck-worker",
        signal_sent="SIGKILL",
        success=True,
        port_freed=True,
        message="Killed with SIGKILL",
    )
    with (
        patch("portpilot.process_manager.ProcessManager.get_port_processes", return_value=[target]),
        patch("portpilot.process_manager.ProcessManager.validate_target_process"),
        patch("portpilot.process_manager.ProcessManager.check_safety_warnings", return_value=[]),
        patch(
            "portpilot.process_manager.ProcessManager.terminate_process", return_value=mock_result
        ),
    ):
        code = run_cli(["stop", "8000", "--sigkill", "--yes", "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Killed with SIGKILL" in captured.out


def test_cli_stop_interactive_confirmation_yes(capsys):
    target = ProcessInfo(pid=6666, name="worker")
    mock_result = StopResult(
        port=8000,
        pid=6666,
        process_name="worker",
        signal_sent="SIGTERM",
        success=True,
        port_freed=True,
        message="Stopped",
    )
    with (
        patch("portpilot.process_manager.ProcessManager.get_port_processes", return_value=[target]),
        patch("portpilot.process_manager.ProcessManager.validate_target_process"),
        patch("portpilot.process_manager.ProcessManager.check_safety_warnings", return_value=[]),
        patch("builtins.input", return_value="y"),
        patch(
            "portpilot.process_manager.ProcessManager.terminate_process", return_value=mock_result
        ),
    ):
        code = run_cli(["stop", "8000", "--no-color"])
        assert code == 0
        captured = capsys.readouterr()
        assert "[SUCCESS]" in captured.out


def test_main_entrypoint():
    with patch("sys.exit") as mock_exit, patch("portpilot.cli.run_cli", return_value=0):
        from portpilot.main import main

        main()
        mock_exit.assert_called_once_with(0)
