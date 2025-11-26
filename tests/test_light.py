"""Tests for Crestron Light platform."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add custom_components to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.crestron.light import CrestronLight


class TestCrestronLight:
    """Tests for CrestronLight entity."""

    def test_light_init(self, mock_hub):
        """Test light initializes with correct name and joins."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config)

        assert light._name == "Test Light"
        assert light._brightness_join == 1
        assert light._hub == mock_hub
        assert light._from_ui is False
        assert light._is_dimmer_light is False

    def test_light_init_from_ui(self, mock_hub):
        """Test light initializes with from_ui flag."""
        config = {
            "name": "UI Light",
            "type": "brightness",
            "brightness_join": 5,
        }

        light = CrestronLight(mock_hub, config, from_ui=True)

        assert light._from_ui is True
        assert light._name == "UI Light"

    def test_light_init_dimmer_light(self, mock_hub):
        """Test dimmer light initializes with device grouping."""
        config = {
            "name": "Light",
            "type": "brightness",
            "brightness_join": 10,
        }

        light = CrestronLight(mock_hub, config, from_ui=True, is_dimmer_light=True, dimmer_name="Kitchen")

        assert light._is_dimmer_light is True
        assert light._dimmer_name == "Kitchen"
        assert light._name == "Light"

    def test_light_unique_id_yaml(self, mock_hub):
        """Test unique_id format for YAML-configured lights."""
        config = {
            "name": "YAML Light",
            "type": "brightness",
            "brightness_join": 42,
        }

        light = CrestronLight(mock_hub, config)

        assert light.unique_id == "crestron_light_a42"

    def test_light_unique_id_ui(self, mock_hub):
        """Test unique_id format for UI-configured lights."""
        config = {
            "name": "UI Light",
            "type": "brightness",
            "brightness_join": 42,
        }

        light = CrestronLight(mock_hub, config, from_ui=True)

        assert light.unique_id == "crestron_light_ui_a42"

    def test_light_unique_id_dimmer(self, mock_hub):
        """Test unique_id format for dimmer lights."""
        config = {
            "name": "Light",
            "type": "brightness",
            "brightness_join": 42,
        }

        light = CrestronLight(mock_hub, config, from_ui=True, is_dimmer_light=True, dimmer_name="Kitchen")

        assert light.unique_id == "crestron_light_dimmer_Kitchen_a42"

    def test_light_is_on_from_hub_true(self, mock_hub):
        """Test light reports on when hub has brightness > 0."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        # Simulate hub having brightness value (1-65535 = on)
        mock_hub._analog[1] = 32767  # Mid brightness
        mock_hub._analog_received.add(1)

        light = CrestronLight(mock_hub, config)

        assert light.is_on is True

    def test_light_is_off_from_hub(self, mock_hub):
        """Test light reports off when hub has brightness = 0."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        # Simulate hub having zero brightness
        mock_hub._analog[1] = 0
        mock_hub._analog_received.add(1)

        light = CrestronLight(mock_hub, config)

        assert light.is_on is False

    def test_light_is_on_no_value_received(self, mock_hub):
        """Test light defaults to off when no value received from hub."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        # No value received from hub
        light = CrestronLight(mock_hub, config)

        # Should default to False (off) when no value and no restored state
        assert light.is_on is False

    def test_light_brightness_from_hub(self, mock_hub):
        """Test light returns correct brightness value from hub."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        # Simulate hub having brightness value (65535 = full brightness = 255 in HA)
        mock_hub._analog[1] = 65535
        mock_hub._analog_received.add(1)

        light = CrestronLight(mock_hub, config)

        # 65535 in Crestron = 255 in HA
        assert light.brightness == 255

    def test_light_brightness_scaling(self, mock_hub):
        """Test brightness scaling from Crestron (0-65535) to HA (0-255)."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        # Test mid brightness: 32767 / 65535 * 255 = ~127
        mock_hub._analog[1] = 32767
        mock_hub._analog_received.add(1)

        light = CrestronLight(mock_hub, config)

        assert light.brightness == 127

    def test_light_brightness_zero(self, mock_hub):
        """Test brightness returns 0 when off."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        # Zero brightness
        mock_hub._analog[1] = 0
        mock_hub._analog_received.add(1)

        light = CrestronLight(mock_hub, config)

        assert light.brightness == 0

    def test_light_brightness_no_value_received(self, mock_hub):
        """Test brightness returns None when no value received."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        # No value received from hub
        light = CrestronLight(mock_hub, config)

        # Should return None (no restored state)
        assert light.brightness is None

    @pytest.mark.asyncio
    async def test_light_turn_on_max_brightness(self, mock_hub):
        """Test turning on light calls hub.async_set_analog with max brightness."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config)

        await light.async_turn_on()

        # Should set to max brightness (65535)
        mock_hub.async_set_analog.assert_called_once_with(1, 65535)

    @pytest.mark.asyncio
    async def test_light_turn_on_with_brightness(self, mock_hub):
        """Test turning on light with specific brightness."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config)

        # Turn on with 50% brightness (127 in HA = ~32639 in Crestron)
        await light.async_turn_on(brightness=127)

        # Should scale 127 to Crestron range: 127 * 65535 / 255 = 32639
        mock_hub.async_set_analog.assert_called_once_with(1, 32639)

    @pytest.mark.asyncio
    async def test_light_turn_on_with_full_brightness(self, mock_hub):
        """Test turning on light with full brightness (255)."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config)

        await light.async_turn_on(brightness=255)

        # Should scale 255 to 65535
        mock_hub.async_set_analog.assert_called_once_with(1, 65535)

    @pytest.mark.asyncio
    async def test_light_turn_on_with_low_brightness(self, mock_hub):
        """Test turning on light with low brightness (1)."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config)

        await light.async_turn_on(brightness=1)

        # Should scale 1 to Crestron range: 1 * 65535 / 255 = 257
        mock_hub.async_set_analog.assert_called_once_with(1, 257)

    @pytest.mark.asyncio
    async def test_light_turn_off(self, mock_hub):
        """Test turning off light calls hub.async_set_analog with 0."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config)

        await light.async_turn_off()

        # Should set to 0
        mock_hub.async_set_analog.assert_called_once_with(1, 0)

    def test_light_available_true(self, mock_hub):
        """Test light reports available when hub is available."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        mock_hub.is_available.return_value = True

        light = CrestronLight(mock_hub, config)

        assert light.available is True

    def test_light_available_false(self, mock_hub):
        """Test light reports unavailable when hub is unavailable."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        mock_hub.is_available.return_value = False

        light = CrestronLight(mock_hub, config)

        assert light.available is False

    def test_light_name(self, mock_hub):
        """Test light name property."""
        config = {
            "name": "Kitchen Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config)

        assert light.name == "Kitchen Light"

    def test_light_has_entity_name_regular(self, mock_hub):
        """Test has_entity_name is False for regular lights."""
        config = {
            "name": "Regular Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config, from_ui=True)

        assert light.has_entity_name is False

    def test_light_has_entity_name_dimmer(self, mock_hub):
        """Test has_entity_name is True for dimmer lights."""
        config = {
            "name": "Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config, from_ui=True, is_dimmer_light=True, dimmer_name="Kitchen")

        assert light.has_entity_name is True

    def test_light_should_poll(self, mock_hub):
        """Test light does not require polling."""
        config = {
            "name": "Test Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config)

        assert light.should_poll is False

    def test_light_device_info_regular(self, mock_hub):
        """Test device_info for regular lights."""
        config = {
            "name": "Regular Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config)
        device_info = light.device_info

        assert device_info["identifiers"] == {("crestron", "crestron_16384")}
        assert device_info["name"] == "Crestron Control System"
        assert device_info["manufacturer"] == "Crestron Electronics"

    def test_light_device_info_dimmer(self, mock_hub):
        """Test device_info for dimmer lights groups under dimmer device."""
        config = {
            "name": "Light",
            "type": "brightness",
            "brightness_join": 1,
        }

        light = CrestronLight(mock_hub, config, from_ui=True, is_dimmer_light=True, dimmer_name="Kitchen")
        device_info = light.device_info

        assert device_info["identifiers"] == {("crestron", "dimmer_Kitchen")}
        assert device_info["name"] == "Kitchen"
        assert device_info["manufacturer"] == "Crestron"
        assert device_info["model"] == "Keypad/Dimmer"
