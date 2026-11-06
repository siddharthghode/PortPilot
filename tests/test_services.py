"""Unit tests for portpilot.services ServiceRegistry."""

from portpilot.models import Protocol, ServicePreset
from portpilot.services import CONVENTION_DISCLAIMER, ServiceRegistry


def test_service_registry_loads_defaults():
    registry = ServiceRegistry()
    presets = registry.get_all()
    assert len(presets) >= 15

    # Check prominent services
    pg = registry.get_services_for_port(5432, Protocol.TCP)
    assert any(p.name == "PostgreSQL" for p in pg)

    redis = registry.get_services_for_port(6379, Protocol.TCP)
    assert any(p.name == "Redis" for p in redis)


def test_service_sharing_same_port():
    registry = ServiceRegistry()
    # 3306 has MySQL and MariaDB
    services_3306 = registry.get_service_names_for_port(3306, Protocol.TCP)
    assert "MySQL" in services_3306
    assert "MariaDB" in services_3306

    # 8000 has Django and FastAPI
    services_8000 = registry.get_service_names_for_port(8000, Protocol.TCP)
    assert "Django" in services_8000
    assert "FastAPI" in services_8000


def test_service_registry_custom_presets_and_deduplication():
    custom = [
        ServicePreset(name="CustomApp", port=9999, protocol=Protocol.TCP, description="My app"),
        # Duplicate registration
        ServicePreset(
            name="CustomApp", port=9999, protocol=Protocol.TCP, description="Updated desc"
        ),
    ]
    registry = ServiceRegistry(custom_presets=custom)
    apps = registry.get_services_for_port(9999, Protocol.TCP)
    assert len(apps) == 1
    assert apps[0].name == "CustomApp"
    assert apps[0].description == "Updated desc"


def test_service_registry_get_all_ports():
    registry = ServiceRegistry()
    ports = registry.get_all_ports(Protocol.TCP)
    assert 5432 in ports
    assert 6379 in ports
    assert 80 in ports
    assert sorted(ports) == ports


def test_service_registry_to_dict():
    registry = ServiceRegistry()
    dict_list = registry.to_dict()
    assert isinstance(dict_list, list)
    assert any(d["name"] == "PostgreSQL" and d["port"] == 5432 for d in dict_list)


def test_disclaimer_presence():
    assert "conventions" in CONVENTION_DISCLAIMER.lower()


def test_service_registry_hardcoded_fallback():
    registry = ServiceRegistry()
    registry._presets = []
    registry._load_hardcoded_fallback()
    assert len(registry.get_all()) >= 15
    assert "PostgreSQL" in registry.get_service_names_for_port(5432, Protocol.TCP)
