"""Light entity configuration handler for Crestron XSIG integration."""

import logging
from typing import Any

from homeassistant.const import CONF_NAME, CONF_TYPE
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from ...const import CONF_BRIGHTNESS_JOIN, CONF_LIGHTS

_LOGGER = logging.getLogger(__name__)


class LightEntityHandler:
    """Handler for light entity configuration."""

    flow: Any  # Type is OptionsFlowHandler from config_flow.py

    def __init__(self, flow: Any) -> None:
        """Initialize the light entity handler."""
        self.flow = flow

    async def async_step_add_light(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Add or edit a light entity."""
        errors: dict[str, str] = {}
        is_editing = self.flow._editing_join is not None

        if user_input is not None:
            try:
                name: str | None = user_input.get(CONF_NAME)
                brightness_join: str | None = user_input.get(CONF_BRIGHTNESS_JOIN)
                light_type: str = user_input.get(CONF_TYPE, "brightness")

                # Validate brightness_join format (must be analog)
                if not brightness_join or not (brightness_join[0] == "a" and brightness_join[1:].isdigit()):
                    errors[CONF_BRIGHTNESS_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_lights: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_LIGHTS, [])
                old_name: str | None = self.flow._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(l.get(CONF_NAME) == name for l in current_lights):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new light entry
                    new_light: dict[str, Any] = {
                        CONF_NAME: name,
                        CONF_BRIGHTNESS_JOIN: brightness_join,
                        CONF_TYPE: light_type,
                    }

                    if is_editing:
                        # Replace existing light
                        updated_lights: list[dict[str, Any]] = [
                            new_light if l.get(CONF_NAME) == old_name else l for l in current_lights
                        ]
                        _LOGGER.info("Updated light %s", name)
                    else:
                        # Append new light
                        updated_lights: list[dict[str, Any]] = current_lights + [new_light]
                        _LOGGER.info("Added light %s", name)

                    # Update config entry
                    new_data: dict[str, Any] = dict(self.flow.config_entry.data)
                    new_data[CONF_LIGHTS] = updated_lights

                    self.flow.hass.config_entries.async_update_entry(self.flow.config_entry, data=new_data)

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating light: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values: dict[str, Any] = {}
        if is_editing:
            default_values = {
                CONF_NAME: self.flow._editing_join.get(CONF_NAME, ""),
                CONF_BRIGHTNESS_JOIN: self.flow._editing_join.get(CONF_BRIGHTNESS_JOIN, ""),
                CONF_TYPE: self.flow._editing_join.get(CONF_TYPE, "brightness"),
            }

        # Show form
        add_light_schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(
                    CONF_BRIGHTNESS_JOIN, default=default_values.get(CONF_BRIGHTNESS_JOIN, "")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_TYPE, default=default_values.get(CONF_TYPE, "brightness")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Dimmable (Brightness)", "value": "brightness"},
                            {"label": "On/Off Only", "value": "onoff"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_light",
            data_schema=add_light_schema,
            errors=errors,
        )
