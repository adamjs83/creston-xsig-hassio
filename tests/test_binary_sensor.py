"""Tests for Crestron Binary Sensor platform."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add custom_components to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.crestron.binary_sensor import CrestronBinarySensor


class TestCrestronBinarySensor:
    """Tests for CrestronBinarySensor entity."""

    def test_binary_sensor_init(self, mock_hub):
        """Test binary sensor initializes correctly."""
        config = {
            "name": "Test Motion Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor._name == "Test Motion Sensor"
        assert sensor._join == 1
        assert sensor._device_class == "motion"
        assert sensor._hub == mock_hub
        assert sensor._from_ui is False

    def test_binary_sensor_init_from_ui(self, mock_hub):
        """Test binary sensor initializes with from_ui flag."""
        config = {
            "name": "UI Motion Sensor",
            "is_on_join": 5,
            "device_class": "motion",
        }

        sensor = CrestronBinarySensor(mock_hub, config, from_ui=True)

        assert sensor._from_ui is True
        assert sensor._name == "UI Motion Sensor"
        assert sensor._join == 5

    def test_binary_sensor_init_door_sensor(self, mock_hub):
        """Test binary sensor with door device class."""
        config = {
            "name": "Front Door",
            "is_on_join": 10,
            "device_class": "door",
        }

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor._device_class == "door"
        assert sensor._name == "Front Door"

    def test_binary_sensor_unique_id_yaml(self, mock_hub):
        """Test unique_id format for YAML-configured sensors."""
        config = {
            "name": "YAML Sensor",
            "is_on_join": 42,
            "device_class": "motion",
        }

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.unique_id == "crestron_binary_sensor_d42"

    def test_binary_sensor_unique_id_ui(self, mock_hub):
        """Test unique_id format for UI-configured sensors."""
        config = {
            "name": "UI Sensor",
            "is_on_join": 42,
            "device_class": "motion",
        }

        sensor = CrestronBinarySensor(mock_hub, config, from_ui=True)

        assert sensor.unique_id == "crestron_binary_sensor_ui_d42"

    def test_binary_sensor_is_on_true(self, mock_hub):
        """Test sensor reports on when hub digital join is True."""
        config = {
            "name": "Test Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        # Simulate hub having digital value = True
        mock_hub._digital[1] = True
        mock_hub._digital_received.add(1)

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.is_on is True

    def test_binary_sensor_is_on_false(self, mock_hub):
        """Test sensor reports off when hub digital join is False."""
        config = {
            "name": "Test Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        # Simulate hub having digital value = False
        mock_hub._digital[1] = False
        mock_hub._digital_received.add(1)

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.is_on is False

    def test_binary_sensor_is_on_no_value_received(self, mock_hub):
        """Test sensor returns None when no value received from hub."""
        config = {
            "name": "Test Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        # No value received from hub
        sensor = CrestronBinarySensor(mock_hub, config)

        # Should return None (no restored state)
        assert sensor.is_on is None

    def test_binary_sensor_available_true(self, mock_hub):
        """Test sensor reports available when hub is available."""
        config = {
            "name": "Test Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        mock_hub.is_available.return_value = True

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.available is True

    def test_binary_sensor_available_false(self, mock_hub):
        """Test sensor reports unavailable when hub is unavailable."""
        config = {
            "name": "Test Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        mock_hub.is_available.return_value = False

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.available is False

    def test_binary_sensor_device_class_motion(self, mock_hub):
        """Test sensor returns motion device class."""
        config = {
            "name": "Motion Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.device_class == "motion"

    def test_binary_sensor_device_class_door(self, mock_hub):
        """Test sensor returns door device class."""
        config = {
            "name": "Door Sensor",
            "is_on_join": 2,
            "device_class": "door",
        }

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.device_class == "door"

    def test_binary_sensor_device_class_window(self, mock_hub):
        """Test sensor returns window device class."""
        config = {
            "name": "Window Sensor",
            "is_on_join": 3,
            "device_class": "window",
        }

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.device_class == "window"

    def test_binary_sensor_device_class_occupancy(self, mock_hub):
        """Test sensor returns occupancy device class."""
        config = {
            "name": "Occupancy Sensor",
            "is_on_join": 4,
            "device_class": "occupancy",
        }

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.device_class == "occupancy"

    def test_binary_sensor_name(self, mock_hub):
        """Test sensor name property."""
        config = {
            "name": "Kitchen Motion",
            "is_on_join": 1,
            "device_class": "motion",
        }

        sensor = CrestronBinarySensor(mock_hub, config)

        assert sensor.name == "Kitchen Motion"

    def test_binary_sensor_device_info(self, mock_hub):
        """Test device_info for binary sensors."""
        config = {
            "name": "Test Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        sensor = CrestronBinarySensor(mock_hub, config)
        device_info = sensor.device_info

        assert device_info["identifiers"] == {("crestron", "crestron_16384")}
        assert device_info["name"] == "Crestron Control System"
        assert device_info["manufacturer"] == "Crestron Electronics"
        assert device_info["model"] == "XSIG Gateway"

    def test_binary_sensor_state_changes_with_hub(self, mock_hub):
        """Test sensor state changes when hub value changes."""
        config = {
            "name": "Test Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        # Initially off
        mock_hub._digital[1] = False
        mock_hub._digital_received.add(1)

        sensor = CrestronBinarySensor(mock_hub, config)
        assert sensor.is_on is False

        # Change to on
        mock_hub._digital[1] = True
        assert sensor.is_on is True

        # Change back to off
        mock_hub._digital[1] = False
        assert sensor.is_on is False

    def test_binary_sensor_different_joins(self, mock_hub):
        """Test multiple sensors with different joins work independently."""
        config1 = {
            "name": "Sensor 1",
            "is_on_join": 1,
            "device_class": "motion",
        }
        config2 = {
            "name": "Sensor 2",
            "is_on_join": 2,
            "device_class": "door",
        }

        # Set different values for different joins
        mock_hub._digital[1] = True
        mock_hub._digital[2] = False
        mock_hub._digital_received.add(1)
        mock_hub._digital_received.add(2)

        sensor1 = CrestronBinarySensor(mock_hub, config1)
        sensor2 = CrestronBinarySensor(mock_hub, config2)

        assert sensor1.is_on is True
        assert sensor2.is_on is False
        assert sensor1.unique_id != sensor2.unique_id

    def test_binary_sensor_yaml_vs_ui_unique_ids(self, mock_hub):
        """Test YAML and UI sensors with same join have different unique IDs."""
        config = {
            "name": "Test Sensor",
            "is_on_join": 1,
            "device_class": "motion",
        }

        yaml_sensor = CrestronBinarySensor(mock_hub, config, from_ui=False)
        ui_sensor = CrestronBinarySensor(mock_hub, config, from_ui=True)

        assert yaml_sensor.unique_id == "crestron_binary_sensor_d1"
        assert ui_sensor.unique_id == "crestron_binary_sensor_ui_d1"
        assert yaml_sensor.unique_id != ui_sensor.unique_id
