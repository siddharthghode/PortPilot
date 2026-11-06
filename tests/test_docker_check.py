"""Unit tests for Docker Compose configuration parsing and preflight verification."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from portpilot.docker_check import DockerComposeChecker
from portpilot.exceptions import ComposeError
from portpilot.models import PortInfo, PortStatus, Protocol


def test_parse_valid_compose_file(tmp_compose_file: Path):
    checker = DockerComposeChecker()
    mappings, warnings = checker.parse_compose_file(tmp_compose_file)

    assert len(mappings) >= 4
    # web: 8080:80
    web_map = next(m for m in mappings if m.service_name == "web")
    assert web_map.host_port == 8080
    assert web_map.container_port == 80
    assert web_map.protocol == Protocol.TCP
    assert web_map.is_dynamic is False

    # db: 127.0.0.1:5432:5432
    db_map = next(m for m in mappings if m.service_name == "db")
    assert db_map.host_ip == "127.0.0.1"
    assert db_map.host_port == 5432
    assert db_map.container_port == 5432

    # cache (long syntax): published: 6379, target: 6379
    cache_map = next(m for m in mappings if m.service_name == "cache")
    assert cache_map.host_port == 6379
    assert cache_map.container_port == 6379

    # worker: single port "3000" (dynamic host mapping)
    worker_map = next(m for m in mappings if m.service_name == "worker")
    assert worker_map.is_dynamic is True


def test_parse_udp_port_mapping(tmp_path: Path):
    compose_path = tmp_path / "docker-compose.yml"
    compose_path.write_text(
        """
services:
  dns:
    image: coredns/coredns
    ports:
      - "53:53/udp"
""".strip(),
        encoding="utf-8",
    )

    checker = DockerComposeChecker()
    mappings, _ = checker.parse_compose_file(compose_path)

    assert len(mappings) == 1
    assert mappings[0].protocol == Protocol.UDP
    assert mappings[0].host_port == 53


def test_parse_port_ranges(tmp_path: Path):
    compose_path = tmp_path / "docker-compose.yml"
    compose_path.write_text(
        """
services:
  app:
    image: test:latest
    ports:
      - "8000-8002:8000-8002"
""".strip(),
        encoding="utf-8",
    )

    checker = DockerComposeChecker()
    mappings, _ = checker.parse_compose_file(compose_path)

    assert len(mappings) == 3
    assert [m.host_port for m in mappings] == [8000, 8001, 8002]


def test_env_var_substitution_in_compose(tmp_path: Path):
    compose_path = tmp_path / "docker-compose.yml"
    compose_path.write_text(
        """
services:
  app:
    image: test:latest
    ports:
      - "${APP_PORT:-9090}:80"
  db:
    image: test:latest
    ports:
      - "${UNSET_VAR}:5432"
""".strip(),
        encoding="utf-8",
    )

    checker = DockerComposeChecker()
    mappings, warnings = checker.parse_compose_file(compose_path)

    # APP_PORT resolved via default to 9090
    assert any(m.host_port == 9090 for m in mappings)
    # UNSET_VAR generates an explicit warning
    assert any("UNSET_VAR" in w for w in warnings)


def test_invalid_compose_file(tmp_path: Path):
    checker = DockerComposeChecker()

    # File not found
    with pytest.raises(ComposeError, match="not found"):
        checker.find_compose_file(tmp_path / "nonexistent.yml")

    # Invalid YAML
    bad_yaml = tmp_path / "bad.yml"
    bad_yaml.write_text(": : bad yaml ::", encoding="utf-8")
    with pytest.raises(ComposeError, match="syntax error"):
        checker.parse_compose_file(bad_yaml)

    # Root not a dictionary
    list_yaml = tmp_path / "list.yml"
    list_yaml.write_text("- item1\n- item2", encoding="utf-8")
    with pytest.raises(ComposeError, match="root must be a mapping"):
        checker.parse_compose_file(list_yaml)


def test_run_preflight_conflict_detection(tmp_compose_file: Path):
    mock_scanner = MagicMock()

    # Mock scanning port 8080 as OCCUPIED, others as AVAILABLE
    def mock_scan_ports(ports):
        results = []
        for p in ports:
            status = PortStatus.OCCUPIED if p == 8080 else PortStatus.AVAILABLE
            results.append(
                PortInfo(
                    port=p,
                    protocol=Protocol.TCP,
                    status=status,
                    processes=[],
                )
            )
        return results

    mock_scanner.scan_ports.side_effect = mock_scan_ports

    checker = DockerComposeChecker(scanner=mock_scanner)
    result = checker.run_preflight(tmp_compose_file)

    assert result.has_conflicts is True
    assert len(result.conflicts) == 1
    assert result.conflicts[0].host_port == 8080
    assert result.conflicts[0].service_name == "web"


def test_find_compose_file_default_search(tmp_path: Path):
    checker = DockerComposeChecker()
    compose_file = tmp_path / "compose.yaml"
    compose_file.write_text("services: {}\n", encoding="utf-8")

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        found = checker.find_compose_file()
        assert found == compose_file


def test_parse_compose_empty_services(tmp_path: Path):
    compose_file = tmp_path / "compose.yaml"
    compose_file.write_text("services: {}\n", encoding="utf-8")
    checker = DockerComposeChecker()
    mappings, warnings = checker.parse_compose_file(compose_file)
    assert mappings == []
    assert any("No services" in w for w in warnings)


def test_parse_long_syntax_unresolved_env(tmp_path: Path):
    compose_file = tmp_path / "compose.yaml"
    compose_file.write_text(
        """
services:
  web:
    image: nginx
    ports:
      - target: 80
        published: "${UNSET_PORT}"
""".strip(),
        encoding="utf-8",
    )
    checker = DockerComposeChecker()
    mappings, warnings = checker.parse_compose_file(compose_file)
    assert mappings == []
    assert any("UNSET_PORT" in w for w in warnings)
