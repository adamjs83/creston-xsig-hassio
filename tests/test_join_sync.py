"""Tests for join synchronization coercion logic."""

import os
import sys

import pytest

# Add custom_components to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.crestron import CrestronHub, _validate_from_joins


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


class TestFromJoinValidation:
    """Tests for from_join script validation at config entry load."""

    def test_service_step_validates(self):
        """UI-stored `service` steps should validate into a runnable script."""
        from_joins = [{"join": "d1", "script": [{"service": "light.toggle", "target": {"entity_id": "light.kitchen"}}]}]

        validated = _validate_from_joins(from_joins)

        assert len(validated) == 1
        assert validated[0]["join"] == "d1"
        step = validated[0]["script"][0]
        assert step.get("action", step.get("service")) == "light.toggle"

    def test_dual_key_step_is_repaired(self):
        """Steps stored with both `action` and `service` should still validate."""
        from_joins = [{"join": "d2", "script": [{"action": "light.toggle", "service": "light.toggle"}]}]

        validated = _validate_from_joins(from_joins)

        assert len(validated) == 1

    def test_invalid_script_is_skipped(self):
        """An invalid join should be dropped without affecting the others."""
        from_joins = [
            {"join": "d3", "script": [{"not_a_real_action": True}]},
            {"join": "d4", "script": [{"service": "light.toggle"}]},
        ]

        validated = _validate_from_joins(from_joins)

        assert [j["join"] for j in validated] == ["d4"]

    def test_service_payload_not_modified(self):
        """Nested `action` keys inside service data must pass through untouched."""
        actions = [{"action": "garage.open", "title": "Open"}]
        from_joins = [
            {
                "join": "d5",
                "script": [{"service": "notify.mobile_app_phone", "data": {"message": "Hi", "data": {"actions": actions}}}],
            }
        ]

        validated = _validate_from_joins(from_joins)

        nested = validated[0]["script"][0]["data"]["data"]
        assert "service" not in str(nested)

    def test_does_not_mutate_stored_config(self):
        """Validation must not mutate the config entry data."""
        step = {"action": "light.toggle", "service": "light.toggle"}
        from_joins = [{"join": "d6", "script": [step]}]

        _validate_from_joins(from_joins)

        assert step == {"action": "light.toggle", "service": "light.toggle"}

    def test_legacy_service_join_passthrough(self):
        """Top-level service/data joins are dispatched directly and left as-is."""
        from_joins = [{"join": "a1", "service": "light.turn_on", "data": {"entity_id": "light.kitchen"}}]

        assert _validate_from_joins(from_joins) == from_joins
