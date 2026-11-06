"""Pytest fixtures and test helpers for PortPilot tests."""

import socket
from collections.abc import Generator
from pathlib import Path

import pytest

from portpilot.models import ProcessInfo


@pytest.fixture
def tcp_test_server() -> Generator[tuple[str, int, socket.socket], None, None]:
    """Create a temporary local TCP listening socket on localhost."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    host, port = sock.getsockname()
    yield host, port, sock
    sock.close()


@pytest.fixture
def udp_test_socket() -> Generator[tuple[str, int, socket.socket], None, None]:
    """Create a temporary local UDP socket bound to localhost."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    yield host, port, sock
    sock.close()


@pytest.fixture
def ipv6_test_server() -> Generator[tuple[str, int, socket.socket] | None, None, None]:
    """Create a temporary IPv6 listening socket on ::1 if supported."""
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("::1", 0))
        sock.listen(1)
        host, port = sock.getsockname()[:2]
        yield host, port, sock
        sock.close()
    except OSError:
        yield None


@pytest.fixture
def sample_process_info() -> ProcessInfo:
    """Provide a sample valid ProcessInfo instance."""
    return ProcessInfo(
        pid=99999,
        name="test_worker",
        username="developer",
        cmdline=["python", "worker.py", "--port", "8000"],
        status="running",
        ppid=1000,
        exe="/usr/bin/python3",
        create_time=1700000000.0,
        is_systemd=False,
        is_docker=False,
    )


@pytest.fixture
def tmp_compose_file(tmp_path: Path) -> Path:
    """Create a valid docker-compose.yml file in a temporary directory."""
    compose_path = tmp_path / "docker-compose.yml"
    content = """
services:
  web:
    image: nginx:alpine
    ports:
      - "8080:80"
  db:
    image: postgres:15
    ports:
      - "127.0.0.1:5432:5432"
  cache:
    image: redis:alpine
    ports:
      - target: 6379
        published: 6379
        protocol: tcp
  worker:
    image: busybox
    ports:
      - "3000"
"""
    compose_path.write_text(content.strip(), encoding="utf-8")
    return compose_path
