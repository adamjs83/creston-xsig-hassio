"""Tests for join synchronization coercion logic."""

import os
import sys

import pytest

# Add custom_components to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.crestron import CrestronHub


class TestJoinSyncCoercion:
    """Tests for analog value coercion from template results."""

    def test_coerce_numeric_values(self):
        """Numeric values should be parsed as ints."""
        assert CrestronHub._coerce_analog_value("1.0") == 1
        assert CrestronHub._coerce_analog_value("42") == 42
        assert CrestronHub._coerce_analog_value(7) == 7

    def test_coerce_media_player_states(self):
        """Media player text states should map to 0/1."""
        assert CrestronHub._coerce_analog_value("playing") == 1
        assert CrestronHub._coerce_analog_value("paused") == 0
        assert CrestronHub._coerce_analog_value("idle") == 0
        assert CrestronHub._coerce_analog_value("off") == 0

    def test_coerce_unknown_state_raises(self):
        """Unsupported textual values should raise ValueError."""
        with pytest.raises(ValueError):
            CrestronHub._coerce_analog_value("not_a_number")


class TestScriptNormalization:
    """Tests for script action normalization compatibility helper."""

    def test_normalize_action_to_service(self):
        """`action` should be converted to `service` for script calls."""
        source = [{"action": "light.toggle"}]
        normalized = CrestronHub._normalize_script_config(source)

        assert normalized[0]["service"] == "light.toggle"

    def test_normalize_service_data_to_data(self):
        """`service_data` should also be available as `data`."""
        source = [{"action": "light.turn_on", "service_data": {"entity_id": "light.kitchen"}}]
        normalized = CrestronHub._normalize_script_config(source)

        assert normalized[0]["data"] == {"entity_id": "light.kitchen"}

    def test_normalize_nested_sequences(self):
        """Nested action entries in choose/default blocks should be normalized."""
        source = [
            {
                "choose": [
                    {
                        "conditions": [],
                        "sequence": [{"action": "switch.turn_on"}],
                    }
                ],
                "default": [{"action": "switch.turn_off"}],
            }
        ]
        normalized = CrestronHub._normalize_script_config(source)

        assert normalized[0]["choose"][0]["sequence"][0]["service"] == "switch.turn_on"
        assert normalized[0]["default"][0]["service"] == "switch.turn_off"
