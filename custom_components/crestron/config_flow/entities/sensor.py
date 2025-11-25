"""Sensor entity configuration handler for Crestron XSIG integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from ...const import (
    CONF_SENSORS,
    CONF_VALUE_JOIN,
    CONF_DIVISOR,
)
from homeassistant.const import CONF_NAME, CONF_DEVICE_CLASS, CONF_UNIT_OF_MEASUREMENT

_LOGGER = logging.getLogger(__name__)


class SensorEntityHandler:
    """Handler for sensor entity configuration."""

    flow: Any  # Type is OptionsFlowHandler from config_flow.py

    def __init__(self, flow: Any) -> None:
        """Initialize the sensor entity handler."""
        self.flow = flow

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a sensor entity."""
        errors: dict[str, str] = {}
        is_editing = self.flow._editing_join is not None

        if user_input is not None:
            try:
                name: str | None = user_input.get(CONF_NAME)
                value_join: str | None = user_input.get(CONF_VALUE_JOIN)
                device_class: str | None = user_input.get(CONF_DEVICE_CLASS)
                unit_of_measurement: str | None = user_input.get(CONF_UNIT_OF_MEASUREMENT)
                divisor: int = user_input.get(CONF_DIVISOR, 1)

                # Validate value_join format (must be analog)
                if not value_join or not (value_join[0] == 'a' and value_join[1:].isdigit()):
                    errors[CONF_VALUE_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_sensors: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_SENSORS, [])
                old_name: str | None = self.flow._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(s.get(CONF_NAME) == name for s in current_sensors):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new sensor entry
                    new_sensor: dict[str, Any] = {
                        CONF_NAME: name,
                        CONF_VALUE_JOIN: value_join,
                        CONF_DEVICE_CLASS: device_class,
                        CONF_UNIT_OF_MEASUREMENT: unit_of_measurement,
                        CONF_DIVISOR: divisor,
                    }

                    if is_editing:
                        # Replace existing sensor
                        updated_sensors: list[dict[str, Any]] = [
                            new_sensor if s.get(CONF_NAME) == old_name else s
                            for s in current_sensors
                        ]
                        _LOGGER.info("Updated sensor %s", name)
                    else:
                        # Append new sensor
                        updated_sensors: list[dict[str, Any]] = current_sensors + [new_sensor]
                        _LOGGER.info("Added sensor %s", name)

                    # Update config entry
                    new_data: dict[str, Any] = dict(self.flow.config_entry.data)
                    new_data[CONF_SENSORS] = updated_sensors

                    self.flow.hass.config_entries.async_update_entry(
                        self.flow.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating sensor: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values: dict[str, Any] = {}
        if is_editing:
            default_values = {
                CONF_NAME: self.flow._editing_join.get(CONF_NAME, ""),
                CONF_VALUE_JOIN: self.flow._editing_join.get(CONF_VALUE_JOIN, ""),
                CONF_DEVICE_CLASS: self.flow._editing_join.get(CONF_DEVICE_CLASS, "temperature"),
                CONF_UNIT_OF_MEASUREMENT: self.flow._editing_join.get(CONF_UNIT_OF_MEASUREMENT, ""),
                CONF_DIVISOR: self.flow._editing_join.get(CONF_DIVISOR, 1),
            }

        # Show form
        add_sensor_schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_VALUE_JOIN, default=default_values.get(CONF_VALUE_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_DEVICE_CLASS, default=default_values.get(CONF_DEVICE_CLASS, "temperature")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Temperature", "value": "temperature"},
                            {"label": "Humidity", "value": "humidity"},
                            {"label": "Pressure", "value": "pressure"},
                            {"label": "Power", "value": "power"},
                            {"label": "Energy", "value": "energy"},
                            {"label": "Voltage", "value": "voltage"},
                            {"label": "Current", "value": "current"},
                            {"label": "Illuminance", "value": "illuminance"},
                            {"label": "Battery", "value": "battery"},
                            {"label": "None", "value": "none"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_UNIT_OF_MEASUREMENT, default=default_values.get(CONF_UNIT_OF_MEASUREMENT, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_DIVISOR, default=default_values.get(CONF_DIVISOR, 1)): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=1000,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_sensor",
            data_schema=add_sensor_schema,
            errors=errors,
        )
