"""Unit tests for OutputFormatter."""

from portpilot.formatter import OutputFormatter
from portpilot.models import (
    ComposePreflightResult,
    PortInfo,
    PortStatus,
    ProcessInfo,
    Protocol,
    ServicePreset,
    StopResult,
)


def test_formatter_banner(capsys):
    formatter = OutputFormatter(color_enabled=False)
    formatter.print_banner()
    captured = capsys.readouterr()
    assert "PORTPILOT" in captured.out


def test_formatter_check_results_multi_process():
    formatter = OutputFormatter(color_enabled=False)
    p1 = ProcessInfo(pid=1001, name="worker1", username="user1")
    p2 = ProcessInfo(pid=1002, name="worker2", username="user2")
    info = PortInfo(
        port=8080,
        protocol=Protocol.TCP,
        status=PortStatus.OCCUPIED,
        local_address="0.0.0.0:8080",
        processes=[p1, p2],
        services=["Custom"],
    )

    out = formatter.format_check_results([info], as_json=False)
    assert "8080" in out
    assert "worker1" in out
    assert "worker2" in out
    assert "Found 1 occupied port" in out


def test_formatter_inspect_empty_and_restricted():
    formatter = OutputFormatter(color_enabled=False)

    # Empty available port
    avail = PortInfo(port=9999, protocol=Protocol.TCP, status=PortStatus.AVAILABLE)
    out_avail = formatter.format_inspect(avail)
    assert "Processes:     None" in out_avail

    # Restricted occupied port without PID
    restr = PortInfo(port=80, protocol=Protocol.TCP, status=PortStatus.OCCUPIED, processes=[])
    out_restr = formatter.format_inspect(restr)
    assert "No PID identifiable" in out_restr


def test_formatter_inspect_json():
    formatter = OutputFormatter(color_enabled=False)
    info = PortInfo(port=80, protocol=Protocol.TCP, status=PortStatus.AVAILABLE)
    json_out = formatter.format_inspect(info, as_json=True)
    assert '"port": 80' in json_out


def test_formatter_services_json():
    formatter = OutputFormatter(color_enabled=False)
    presets = [ServicePreset(name="TestSvc", port=1234, protocol=Protocol.TCP)]
    json_out = formatter.format_services(presets, as_json=True)
    assert "TestSvc" in json_out


def test_formatter_preflight_warnings_and_json():
    formatter = OutputFormatter(color_enabled=False)
    res = ComposePreflightResult(
        compose_file="docker-compose.yml",
        mappings=[],
        conflicts=[],
        warnings=["Unresolved environment variable PORT"],
    )

    text_out = formatter.format_preflight(res, as_json=False)
    assert "WARNINGS:" in text_out
    assert "Unresolved environment variable PORT" in text_out

    json_out = formatter.format_preflight(res, as_json=True)
    assert '"warnings": [' in json_out


def test_formatter_stop_results():
    formatter = OutputFormatter(color_enabled=False)

    # Failure
    fail_res = StopResult(
        port=80,
        pid=123,
        process_name="test",
        signal_sent="SIGTERM",
        success=False,
        port_freed=False,
        message="Did not stop",
    )
    assert "[FAILURE]" in formatter.format_stop_result(fail_res)

    # Success with port still occupied
    warn_res = StopResult(
        port=80,
        pid=123,
        process_name="test",
        signal_sent="SIGTERM",
        success=True,
        port_freed=False,
        message="Stopped",
    )
    assert "remains occupied" in formatter.format_stop_result(warn_res)

    # JSON output
    assert '"success": false' in formatter.format_stop_result(fail_res, as_json=True)
