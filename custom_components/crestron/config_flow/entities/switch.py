"""Switch entity configuration handler for Crestron XSIG integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from ...const import (
    CONF_SWITCHES,
    CONF_SWITCH_JOIN,
)
from homeassistant.const import CONF_NAME, CONF_DEVICE_CLASS

_LOGGER = logging.getLogger(__name__)


class SwitchEntityHandler:
    """Handler for switch entity configuration."""

    flow: Any  # Type is OptionsFlowHandler from config_flow.py

    def __init__(self, flow: Any) -> None:
        """Initialize the switch entity handler."""
        self.flow = flow

    async def async_step_add_switch(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a switch entity."""
        errors: dict[str, str] = {}
        is_editing = self.flow._editing_join is not None

        if user_input is not None:
            try:
                name: str | None = user_input.get(CONF_NAME)
                switch_join: str | None = user_input.get(CONF_SWITCH_JOIN)
                device_class: str = user_input.get(CONF_DEVICE_CLASS, "switch")

                # Validate switch_join format (must be digital)
                if not switch_join or not (switch_join[0] == 'd' and switch_join[1:].isdigit()):
                    errors[CONF_SWITCH_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_switches: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_SWITCHES, [])
                old_name: str | None = self.flow._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(s.get(CONF_NAME) == name for s in current_switches):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new switch entry
                    new_switch: dict[str, Any] = {
                        CONF_NAME: name,
                        CONF_SWITCH_JOIN: switch_join,
                        CONF_DEVICE_CLASS: device_class,
                    }

                    if is_editing:
                        # Replace existing switch
                        updated_switches: list[dict[str, Any]] = [
                            new_switch if s.get(CONF_NAME) == old_name else s
                            for s in current_switches
                        ]
                        _LOGGER.info("Updated switch %s", name)
                    else:
                        # Append new switch
                        updated_switches: list[dict[str, Any]] = current_switches + [new_switch]
                        _LOGGER.info("Added switch %s", name)

                    # Update config entry
                    new_data: dict[str, Any] = dict(self.flow.config_entry.data)
                    new_data[CONF_SWITCHES] = updated_switches

                    self.flow.hass.config_entries.async_update_entry(
                        self.flow.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating switch: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values: dict[str, Any] = {}
        if is_editing:
            default_values = {
                CONF_NAME: self.flow._editing_join.get(CONF_NAME, ""),
                CONF_SWITCH_JOIN: self.flow._editing_join.get(CONF_SWITCH_JOIN, ""),
                CONF_DEVICE_CLASS: self.flow._editing_join.get(CONF_DEVICE_CLASS, "switch"),
            }

        # Show form
        add_switch_schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_SWITCH_JOIN, default=default_values.get(CONF_SWITCH_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_DEVICE_CLASS, default=default_values.get(CONF_DEVICE_CLASS, "switch")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Switch", "value": "switch"},
                            {"label": "Outlet", "value": "outlet"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_switch",
            data_schema=add_switch_schema,
            errors=errors,
        )
