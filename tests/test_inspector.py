"""Unit tests for ProcessInspector and systemd/docker detection."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import psutil

from portpilot.inspector import (
    ProcessInspector,
    detect_docker_container,
    detect_systemd_service,
)


def test_inspect_current_process():
    pid = os.getpid()
    inspector = ProcessInspector()
    info = inspector.inspect_pid(pid)

    assert info.pid == pid
    assert info.name is not None
    assert info.status is not None
    assert info.create_time is not None


def test_inspect_nonexistent_process():
    inspector = ProcessInspector()
    # High PID unlikely to exist
    fake_pid = 4194300
    info = inspector.inspect_pid(fake_pid)

    assert info.pid == fake_pid
    assert info.status == "terminated"
    assert "<process-exited>" in info.name


def test_inspect_access_denied_process():
    inspector = ProcessInspector()
    with patch("psutil.Process", side_effect=psutil.AccessDenied(pid=123)):
        info = inspector.inspect_pid(123)
        assert info.pid == 123
        assert info.name == "<access-denied>"
        assert info.username == "<restricted>"


def test_detect_systemd_service_from_cgroup(tmp_path: Path):
    cgroup_content = "0::/system.slice/postgresql.service\n"
    fake_cgroup = tmp_path / "cgroup"
    fake_cgroup.write_text(cgroup_content, encoding="utf-8")

    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.read_text", return_value=cgroup_content),
    ):
        is_systemd, unit = detect_systemd_service(1234)
        assert is_systemd is True
        assert unit == "postgresql.service"


def test_detect_docker_container_from_cgroup_and_cmdline():
    # Via cmdline (docker-proxy)
    is_docker, desc = detect_docker_container(1234, cmdline=["docker-proxy", "-proto", "tcp"])
    assert is_docker is True
    assert "docker-proxy" in (desc or "")

    # Via cgroup
    container_id = "a1b2c3d4e5f60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef"
    cgroup_content = f"0::/docker/{container_id}\n"
    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.read_text", return_value=cgroup_content),
    ):
        is_docker, desc = detect_docker_container(5678, cmdline=["python", "app.py"])
        assert is_docker is True
        assert container_id[:12] in (desc or "")


def test_format_start_time():
    inspector = ProcessInspector()
    assert inspector.format_start_time(None) == "Unknown"
    formatted = inspector.format_start_time(1700000000.0)
    assert "UTC" in formatted


def test_inspect_partial_attribute_access_denied():
    inspector = ProcessInspector()
    mock_proc = MagicMock()
    mock_proc.name.side_effect = psutil.AccessDenied()
    mock_proc.exe.side_effect = psutil.AccessDenied()
    mock_proc.cmdline.side_effect = psutil.NoSuchProcess(1)
    mock_proc.create_time.side_effect = psutil.AccessDenied()
    mock_proc.username.side_effect = psutil.AccessDenied()
    mock_proc.ppid.side_effect = psutil.AccessDenied()
    mock_proc.status.side_effect = psutil.AccessDenied()
    mock_proc.memory_info.side_effect = psutil.AccessDenied()

    with patch("psutil.Process", return_value=mock_proc):
        info = inspector.inspect_pid(9999)
        assert info.pid == 9999
        assert info.name == "unknown"
        assert info.exe is None
        assert info.cmdline is None
