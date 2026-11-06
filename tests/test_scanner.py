"""Unit and integration tests for PortScanner."""

import socket
from unittest.mock import patch

import psutil
import pytest

from portpilot.exceptions import PortValidationError
from portpilot.models import PortStatus, Protocol
from portpilot.scanner import PortScanner


def test_scan_available_tcp_port():
    scanner = PortScanner()
    # Find an unused port by briefly binding and releasing
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    _, unused_port = s.getsockname()
    s.close()

    result = scanner.scan_port(unused_port, Protocol.TCP)
    assert result.port == unused_port
    assert result.status == PortStatus.AVAILABLE
    assert result.processes == []


def test_scan_occupied_tcp_port(tcp_test_server):
    host, port, _ = tcp_test_server
    scanner = PortScanner()

    result = scanner.scan_port(port, Protocol.TCP)
    assert result.port == port
    assert result.status == PortStatus.OCCUPIED
    assert len(result.processes) >= 1
    # Check that our test process is identified
    pids = [p.pid for p in result.processes]
    assert any(pid > 0 for pid in pids)


def test_scan_multiple_ports(tcp_test_server):
    host, occupied_port, _ = tcp_test_server
    scanner = PortScanner()

    # Mix of occupied port and known available port
    unused_port = occupied_port + 1 if occupied_port < 65530 else occupied_port - 1
    results = scanner.scan_ports([occupied_port, unused_port], Protocol.TCP)

    assert len(results) == 2
    occ = next(r for r in results if r.port == occupied_port)
    avail = next(r for r in results if r.port == unused_port)

    assert occ.status == PortStatus.OCCUPIED
    assert avail.status == PortStatus.AVAILABLE


def test_scan_udp_socket(udp_test_socket):
    host, port, _ = udp_test_socket
    scanner = PortScanner()

    result = scanner.scan_port(port, Protocol.UDP)
    assert result.port == port
    assert result.status == PortStatus.OCCUPIED
    assert result.protocol == Protocol.UDP


def test_scan_ipv6_listener(ipv6_test_server):
    if ipv6_test_server is None:
        pytest.skip("IPv6 not supported on this host environment.")

    host, port, _ = ipv6_test_server
    scanner = PortScanner()

    result = scanner.scan_port(port, Protocol.TCP)
    assert result.port == port
    assert result.status == PortStatus.OCCUPIED


def test_permission_denied_scenario():
    scanner = PortScanner()

    with (
        patch("psutil.net_connections", side_effect=psutil.AccessDenied("Permission denied")),
        patch.object(scanner, "_get_sockets_from_ss", return_value={}),
    ):
        result = scanner.scan_port(80, Protocol.TCP)
        assert result.status == PortStatus.PERMISSION_DENIED
        assert "Access denied" in (result.error or "")


def test_ss_address_and_pid_parsing():
    # Test IPv4
    ip, port = PortScanner._parse_ss_address("127.0.0.1:8080")
    assert ip == "127.0.0.1"
    assert port == 8080

    # Test IPv6
    ip6, port6 = PortScanner._parse_ss_address("[::]:5432")
    assert ip6 == "::"
    assert port6 == 5432

    # Test wildcard port
    ip_wc, port_wc = PortScanner._parse_ss_address("0.0.0.0:*")
    assert port_wc is None

    # Test PID parsing from ss process field
    pids = PortScanner._parse_ss_pids(
        'users:(("postgres",pid=1234,fd=5),("postgres",pid=1235,fd=6))'
    )
    assert pids == [1234, 1235]


def test_invalid_port_raises_error():
    scanner = PortScanner()
    with pytest.raises(PortValidationError):
        scanner.scan_port(99999)
