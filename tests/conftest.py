"""Pytest fixtures for Crestron XSIG Integration tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any


@pytest.fixture
def mock_hub():
    """Create a mock CrestronXsig hub."""
    hub = MagicMock()
    hub.port = 16384
    hub._available = True
    hub._digital = {}
    hub._analog = {}
    hub._serial = {}
    hub._digital_received = set()
    hub._analog_received = set()
    hub._callbacks = set()

    # Mock methods
    hub.is_available.return_value = True
    hub.get_digital.side_effect = lambda j: hub._digital.get(j, False)
    hub.get_analog.side_effect = lambda j: hub._analog.get(j, 0)
    hub.get_serial.side_effect = lambda j: hub._serial.get(j, "")
    hub.has_digital_value.side_effect = lambda j: j in hub._digital_received
    hub.has_analog_value.side_effect = lambda j: j in hub._analog_received

    # Track set calls
    def set_digital(join, value):
        hub._digital[join] = value
        hub._digital_received.add(join)

    def set_analog(join, value):
        hub._analog[join] = value
        hub._analog_received.add(join)

    hub.set_digital.side_effect = set_digital
    hub.set_analog.side_effect = set_analog
    hub.async_set_analog = AsyncMock(side_effect=set_analog)
    hub.async_set_digital = AsyncMock(side_effect=set_digital)

    # Callback registration
    def register_callback(cb):
        hub._callbacks.add(cb)

    def remove_callback(cb):
        hub._callbacks.discard(cb)

    hub.register_callback.side_effect = register_callback
    hub.remove_callback.side_effect = remove_callback

    return hub


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.states = MagicMock()
    hass.bus = MagicMock()
    hass.services = MagicMock()
    hass.config_entries = MagicMock()
    hass.config = MagicMock()
    hass.config.units = MagicMock()
    hass.config.units.temperature_unit = "°F"
    return hass


@pytest.fixture
def light_config() -> dict[str, Any]:
    """Return a basic light configuration."""
    return {
        "name": "Test Light",
        "type": "brightness",
        "brightness_join": 1,
    }


@pytest.fixture
def switch_config() -> dict[str, Any]:
    """Return a basic switch configuration."""
    return {
        "name": "Test Switch",
        "switch_join": 1,
        "device_class": "switch",
    }


@pytest.fixture
def cover_config() -> dict[str, Any]:
    """Return a basic cover configuration."""
    return {
        "name": "Test Cover",
        "type": "shade",
        "pos_join": 1,
        "stop_join": 2,
    }


@pytest.fixture
def binary_sensor_config() -> dict[str, Any]:
    """Return a basic binary sensor configuration."""
    return {
        "name": "Test Sensor",
        "is_on_join": 1,
        "device_class": "motion",
    }
