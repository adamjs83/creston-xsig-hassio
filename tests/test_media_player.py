"""Tests for Crestron Media Player platform."""

import os
import sys

import pytest

# Add custom_components to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from homeassistant.components.media_player import MediaPlayerEntityFeature

from custom_components.crestron.media_player import CrestronRoom


class TestCrestronMediaPlayer:
    """Tests for CrestronRoom entity."""

    def test_source_handles_string_source_keys(self, mock_hub):
        """Source lookup should work when persisted config keys are strings."""
        config = {
            "name": "Living Room TV",
            "source_number_join": 41,
            "sources": {"1": "Cable", "2": "Apple TV"},
        }

        mock_hub._analog[41] = 2
        mock_hub._analog_received.add(41)

        media_player = CrestronRoom(mock_hub, config, from_ui=True)

        assert media_player.source == "Apple TV"

    @pytest.mark.asyncio
    async def test_select_source_sends_int_source_number(self, mock_hub):
        """Selecting source should send integer source numbers to analog join."""
        config = {
            "name": "Living Room TV",
            "source_number_join": 41,
            "sources": {"1": "Cable", "2": "Apple TV"},
        }

        media_player = CrestronRoom(mock_hub, config, from_ui=True)

        await media_player.async_select_source("Apple TV")

        mock_hub.async_set_analog.assert_called_once_with(41, 2)

    def test_supported_features_is_enum_type(self, mock_hub):
        """Supported features should be MediaPlayerEntityFeature, not plain int."""
        config = {
            "name": "Living Room TV",
            "source_number_join": 41,
            "sources": {"1": "Cable"},
            "power_on_join": 10,
        }

        media_player = CrestronRoom(mock_hub, config, from_ui=True)

        assert isinstance(media_player.supported_features, MediaPlayerEntityFeature)
