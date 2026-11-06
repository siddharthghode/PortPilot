"""Unit tests for models and data class serializations."""

from portpilot.models import (
    ComposePortMapping,
    ComposePreflightConflict,
    ComposePreflightResult,
    PortInfo,
    PortStatus,
    ProcessInfo,
    Protocol,
    ServicePreset,
    StopResult,
)


def test_models_serialization():
    # Protocol string
    assert str(Protocol.TCP) == "TCP"
    assert str(PortStatus.OCCUPIED) == "OCCUPIED"

    proc = ProcessInfo(pid=100, name="test_proc")
    p_dict = proc.to_dict()
    assert p_dict["pid"] == 100
    assert p_dict["name"] == "test_proc"

    preset = ServicePreset(name="Redis", port=6379, protocol=Protocol.TCP)
    preset_dict = preset.to_dict()
    assert preset_dict["name"] == "Redis"
    assert preset_dict["port"] == 6379

    port_info = PortInfo(
        port=6379,
        protocol=Protocol.TCP,
        status=PortStatus.OCCUPIED,
        processes=[proc],
        services=["Redis"],
    )
    pi_dict = port_info.to_dict()
    assert pi_dict["port"] == 6379
    assert pi_dict["status"] == "OCCUPIED"
    assert len(pi_dict["processes"]) == 1

    mapping = ComposePortMapping(
        service_name="web",
        host_ip="127.0.0.1",
        host_port=80,
        container_port=80,
        protocol=Protocol.TCP,
    )
    m_dict = mapping.to_dict()
    assert m_dict["host_port"] == 80

    conflict = ComposePreflightConflict(
        service_name="web",
        host_port=80,
        host_ip="127.0.0.1",
        protocol=Protocol.TCP,
        port_info=port_info,
    )
    c_dict = conflict.to_dict()
    assert c_dict["service_name"] == "web"

    preflight = ComposePreflightResult(
        compose_file="docker-compose.yml",
        mappings=[mapping],
        conflicts=[conflict],
    )
    pf_dict = preflight.to_dict()
    assert pf_dict["has_conflicts"] is True

    stop_res = StopResult(
        port=80,
        pid=100,
        process_name="test_proc",
        signal_sent="SIGTERM",
        success=True,
        port_freed=True,
        message="Terminated",
        dry_run=False,
    )
    sr_dict = stop_res.to_dict()
    assert sr_dict["success"] is True
