"""Unit tests for ProcessManager safe termination logic."""

import os
import signal
from unittest.mock import MagicMock, patch

import psutil
import pytest

from portpilot.exceptions import CriticalProcessError, ProcessPermissionError
from portpilot.models import PortInfo, PortStatus, ProcessInfo, Protocol
from portpilot.process_manager import ProcessManager


def test_reject_init_pid_1():
    proc_mgr = ProcessManager()
    init_proc = ProcessInfo(pid=1, name="systemd")

    with pytest.raises(CriticalProcessError, match="init / system manager"):
        proc_mgr.validate_target_process(init_proc)


def test_reject_pid_0():
    proc_mgr = ProcessManager()
    kernel_proc = ProcessInfo(pid=0, name="kernel")

    with pytest.raises(CriticalProcessError, match="init / system manager"):
        proc_mgr.validate_target_process(kernel_proc)


def test_reject_portpilot_self_and_parent():
    proc_mgr = ProcessManager()
    self_proc = ProcessInfo(pid=os.getpid(), name="portpilot")
    parent_proc = ProcessInfo(pid=os.getppid(), name="parent_shell")

    with pytest.raises(CriticalProcessError, match="active PortPilot process"):
        proc_mgr.validate_target_process(self_proc)

    with pytest.raises(CriticalProcessError, match="parent process"):
        proc_mgr.validate_target_process(parent_proc)


def test_pid_reuse_detection():
    proc_mgr = ProcessManager()
    # Mock psutil.Process returning a different create_time
    mock_proc = MagicMock()
    mock_proc.create_time.return_value = 2000000000.0

    stale_info = ProcessInfo(pid=99999, name="old_app", create_time=1000000000.0)

    with patch("psutil.Process", return_value=mock_proc):
        with pytest.raises(CriticalProcessError, match="PID reuse detected"):
            proc_mgr.validate_target_process(stale_info)


def test_safety_warnings():
    proc_mgr = ProcessManager()

    info = ProcessInfo(
        pid=5555,
        name="postgres",
        is_systemd=True,
        systemd_service="postgresql.service",
        is_docker=True,
        docker_container_id="c123",
    )

    warnings = proc_mgr.check_safety_warnings(info)
    assert any("systemd" in w for w in warnings)
    assert any("postgresql.service" in w for w in warnings)
    assert any("Docker" in w for w in warnings)
    assert any("database" in w for w in warnings)


def test_dry_run_mode(sample_process_info):
    proc_mgr = ProcessManager()

    with patch.object(proc_mgr, "validate_target_process"):
        res = proc_mgr.terminate_process(
            port=8000,
            proc_info=sample_process_info,
            dry_run=True,
        )

        assert res.dry_run is True
        assert res.signal_sent == "NONE"
        assert "[DRY-RUN]" in res.message


def test_terminate_process_sigterm_success(sample_process_info):
    proc_mgr = ProcessManager()
    mock_proc = MagicMock()

    with (
        patch.object(proc_mgr, "validate_target_process"),
        patch("psutil.Process", return_value=mock_proc),
        patch.object(proc_mgr, "_wait_for_exit", return_value=True),
        patch.object(proc_mgr, "_is_port_freed", return_value=True),
    ):
        res = proc_mgr.terminate_process(
            port=8000,
            proc_info=sample_process_info,
            timeout=2.0,
            dry_run=False,
            use_sigkill=False,
        )

        assert res.success is True
        assert res.port_freed is True
        assert res.signal_sent == "SIGTERM"
        mock_proc.send_signal.assert_called_once_with(signal.SIGTERM)


def test_terminate_process_timeout_grace_period(sample_process_info):
    proc_mgr = ProcessManager()
    mock_proc = MagicMock()

    with (
        patch.object(proc_mgr, "validate_target_process"),
        patch("psutil.Process", return_value=mock_proc),
        patch.object(proc_mgr, "_wait_for_exit", return_value=False),
    ):
        res = proc_mgr.terminate_process(
            port=8000,
            proc_info=sample_process_info,
            timeout=1.0,
            dry_run=False,
            use_sigkill=False,
        )

        assert res.success is False
        assert "did not terminate within" in res.message


def test_terminate_process_sigkill_escalation(sample_process_info):
    proc_mgr = ProcessManager()
    mock_proc = MagicMock()

    with (
        patch.object(proc_mgr, "validate_target_process"),
        patch("psutil.Process", return_value=mock_proc),
        patch.object(proc_mgr, "_wait_for_exit", return_value=True),
        patch.object(proc_mgr, "_is_port_freed", return_value=True),
    ):
        res = proc_mgr.terminate_process(
            port=8000,
            proc_info=sample_process_info,
            timeout=1.0,
            dry_run=False,
            use_sigkill=True,
        )

        assert res.success is True
        assert res.signal_sent == "SIGKILL"
        mock_proc.send_signal.assert_called_once_with(signal.SIGKILL)


def test_validate_target_process_nosuchprocess():
    proc_mgr = ProcessManager()
    with patch("psutil.Process", side_effect=psutil.NoSuchProcess(pid=99999)):
        with pytest.raises(CriticalProcessError, match="no longer exists"):
            proc_mgr.validate_target_process(ProcessInfo(pid=99999, name="gone"))


def test_validate_target_process_access_denied():
    proc_mgr = ProcessManager()
    with patch("psutil.Process", side_effect=psutil.AccessDenied(pid=99999)):
        with pytest.raises(ProcessPermissionError, match="Access denied"):
            proc_mgr.validate_target_process(ProcessInfo(pid=99999, name="root_proc"))


def test_terminate_process_permission_error_on_signal(sample_process_info):
    proc_mgr = ProcessManager()
    mock_proc = MagicMock()
    mock_proc.send_signal.side_effect = PermissionError()

    with (
        patch.object(proc_mgr, "validate_target_process"),
        patch("psutil.Process", return_value=mock_proc),
    ):
        with pytest.raises(ProcessPermissionError, match="Permission denied sending"):
            proc_mgr.terminate_process(
                port=8000,
                proc_info=sample_process_info,
            )


def test_wait_for_exit_zombie():
    proc_mgr = ProcessManager()
    mock_proc = MagicMock()
    mock_proc.is_running.return_value = True
    mock_proc.status.return_value = psutil.STATUS_ZOMBIE
    assert proc_mgr._wait_for_exit(mock_proc, timeout=1.0) is True


def test_get_port_processes():
    mock_scanner = MagicMock()
    mock_scanner.scan_port.return_value = PortInfo(
        port=80,
        protocol=Protocol.TCP,
        status=PortStatus.OCCUPIED,
        processes=[ProcessInfo(pid=123, name="test")],
    )
    proc_mgr = ProcessManager(scanner=mock_scanner)
    procs = proc_mgr.get_port_processes(80)
    assert len(procs) == 1
    assert procs[0].pid == 123
