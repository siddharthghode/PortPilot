"""Unit tests for configuration loading."""

from pathlib import Path

import pytest

from portpilot.config import Config
from portpilot.exceptions import ConfigError
from portpilot.models import Protocol


def test_default_config():
    cfg = Config()
    assert 5432 in cfg.default_ports
    assert cfg.termination_timeout == 5.0
    assert cfg.color is True
    assert cfg.default_protocol == Protocol.TCP


def test_load_toml_config(tmp_path: Path):
    toml_path = tmp_path / "config.toml"
    toml_path.write_text(
        """
default_ports = [3000, 8080, 9000]
termination_timeout = 8.5
color = false
default_protocol = "udp"

[[services]]
name = "MyCustomService"
port = 9000
protocol = "udp"
category = "custom"
description = "Custom test service"
""".strip(),
        encoding="utf-8",
    )

    cfg = Config.load(toml_path)
    assert cfg.default_ports == [3000, 8080, 9000]
    assert cfg.termination_timeout == 8.5
    assert cfg.color is False
    assert cfg.default_protocol == Protocol.UDP
    assert len(cfg.custom_services) == 1
    assert cfg.custom_services[0].name == "MyCustomService"


def test_load_json_config(tmp_path: Path):
    json_path = tmp_path / "config.json"
    json_path.write_text(
        """
{
  "default_ports": [5000, 6000],
  "termination_timeout": 3.0,
  "color": true,
  "services": [
    {
      "name": "JsonService",
      "port": 6000,
      "protocol": "tcp"
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    cfg = Config.load(json_path)
    assert cfg.default_ports == [5000, 6000]
    assert cfg.termination_timeout == 3.0
    assert len(cfg.custom_services) == 1
    assert cfg.custom_services[0].name == "JsonService"


def test_missing_explicit_config_raises_error(tmp_path: Path):
    with pytest.raises(ConfigError, match="does not exist"):
        Config.load(tmp_path / "missing.toml")


def test_malformed_config_raises_error(tmp_path: Path):
    bad_path = tmp_path / "corrupt.toml"
    bad_path.write_text("::invalid toml::", encoding="utf-8")
    with pytest.raises(ConfigError, match="Failed to parse"):
        Config.load(bad_path)


def test_env_var_config_lookup(tmp_path: Path, monkeypatch):
    custom_cfg = tmp_path / "env_config.toml"
    custom_cfg.write_text("default_ports = [1234]\n", encoding="utf-8")
    monkeypatch.setenv("PORTPILOT_CONFIG", str(custom_cfg))

    cfg = Config.load()
    assert cfg.default_ports == [1234]
