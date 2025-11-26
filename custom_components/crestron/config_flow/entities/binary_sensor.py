"""Binary sensor entity configuration handler for Crestron XSIG integration."""

import logging
from typing import Any

from homeassistant.const import CONF_DEVICE_CLASS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from ...const import CONF_BINARY_SENSORS, CONF_IS_ON_JOIN

_LOGGER = logging.getLogger(__name__)


class BinarySensorEntityHandler:
    """Handler for binary sensor entity configuration."""

    flow: Any  # Type is OptionsFlowHandler from config_flow.py

    def __init__(self, flow: Any) -> None:
        """Initialize the binary sensor entity handler."""
        self.flow = flow

    async def async_step_add_binary_sensor(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Add or edit a binary sensor entity."""
        errors: dict[str, str] = {}
        is_editing = self.flow._editing_join is not None

        if user_input is not None:
            try:
                name: str | None = user_input.get(CONF_NAME)
                is_on_join: str | None = user_input.get(CONF_IS_ON_JOIN)
                device_class: str | None = user_input.get(CONF_DEVICE_CLASS)

                # Validate is_on_join format (must be digital)
                if not is_on_join or not (is_on_join[0] == "d" and is_on_join[1:].isdigit()):
                    errors[CONF_IS_ON_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_binary_sensors: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_BINARY_SENSORS, [])
                old_name: str | None = self.flow._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(bs.get(CONF_NAME) == name for bs in current_binary_sensors):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new binary sensor entry
                    new_binary_sensor: dict[str, Any] = {
                        CONF_NAME: name,
                        CONF_IS_ON_JOIN: is_on_join,
                        CONF_DEVICE_CLASS: device_class,
                    }

                    if is_editing:
                        # Replace existing binary sensor
                        updated_binary_sensors: list[dict[str, Any]] = [
                            new_binary_sensor if bs.get(CONF_NAME) == old_name else bs for bs in current_binary_sensors
                        ]
                        _LOGGER.info("Updated binary sensor %s", name)
                    else:
                        # Append new binary sensor
                        updated_binary_sensors: list[dict[str, Any]] = current_binary_sensors + [new_binary_sensor]
                        _LOGGER.info("Added binary sensor %s", name)

                    # Update config entry
                    new_data: dict[str, Any] = dict(self.flow.config_entry.data)
                    new_data[CONF_BINARY_SENSORS] = updated_binary_sensors

                    self.flow.hass.config_entries.async_update_entry(self.flow.config_entry, data=new_data)

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating binary sensor: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values: dict[str, Any] = {}
        if is_editing:
            default_values = {
                CONF_NAME: self.flow._editing_join.get(CONF_NAME, ""),
                CONF_IS_ON_JOIN: self.flow._editing_join.get(CONF_IS_ON_JOIN, ""),
                CONF_DEVICE_CLASS: self.flow._editing_join.get(CONF_DEVICE_CLASS, "motion"),
            }

        # Show form
        add_binary_sensor_schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_IS_ON_JOIN, default=default_values.get(CONF_IS_ON_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(
                    CONF_DEVICE_CLASS, default=default_values.get(CONF_DEVICE_CLASS, "motion")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Motion", "value": "motion"},
                            {"label": "Door", "value": "door"},
                            {"label": "Window", "value": "window"},
                            {"label": "Opening", "value": "opening"},
                            {"label": "Occupancy", "value": "occupancy"},
                            {"label": "Presence", "value": "presence"},
                            {"label": "Garage Door", "value": "garage_door"},
                            {"label": "Smoke", "value": "smoke"},
                            {"label": "Moisture", "value": "moisture"},
                            {"label": "Light", "value": "light"},
                            {"label": "None", "value": "none"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_binary_sensor",
            data_schema=add_binary_sensor_schema,
            errors=errors,
        )
