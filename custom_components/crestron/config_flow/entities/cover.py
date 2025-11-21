"""Cover entity configuration handler for Crestron XSIG integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from ...const import (
    CONF_COVERS,
    CONF_POS_JOIN,
    CONF_IS_OPENING_JOIN,
    CONF_IS_CLOSING_JOIN,
    CONF_IS_CLOSED_JOIN,
    CONF_STOP_JOIN,
)
from homeassistant.const import CONF_NAME, CONF_TYPE

_LOGGER = logging.getLogger(__name__)


class CoverEntityHandler:
    """Handler for cover entity configuration."""

    def __init__(self, flow):
        """Initialize the cover entity handler."""
        self.flow = flow

    async def async_step_add_cover(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a cover entity."""
        errors: dict[str, str] = {}
        is_editing = self.flow._editing_join is not None

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME)
                pos_join = user_input.get(CONF_POS_JOIN)
                entity_type = user_input.get(CONF_TYPE, "shade")
                is_opening_join = user_input.get(CONF_IS_OPENING_JOIN, "").strip()
                is_closing_join = user_input.get(CONF_IS_CLOSING_JOIN, "").strip()
                is_closed_join = user_input.get(CONF_IS_CLOSED_JOIN, "").strip()
                stop_join = user_input.get(CONF_STOP_JOIN, "").strip()

                # Validate pos_join format (must be analog)
                if not pos_join or not (pos_join[0] == 'a' and pos_join[1:].isdigit()):
                    errors[CONF_POS_JOIN] = "invalid_join_format"

                # Validate optional joins format (must be digital if provided)
                for join_field, join_value in [
                    (CONF_IS_OPENING_JOIN, is_opening_join),
                    (CONF_IS_CLOSING_JOIN, is_closing_join),
                    (CONF_IS_CLOSED_JOIN, is_closed_join),
                    (CONF_STOP_JOIN, stop_join),
                ]:
                    if join_value and not (join_value[0] == 'd' and join_value[1:].isdigit()):
                        errors[join_field] = "invalid_join_format"

                # Check for duplicate entity name
                current_covers = self.flow.config_entry.data.get(CONF_COVERS, [])
                old_name = self.flow._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(c.get(CONF_NAME) == name for c in current_covers):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new cover entry
                    new_cover = {
                        CONF_NAME: name,
                        CONF_POS_JOIN: pos_join,
                        CONF_TYPE: entity_type,
                    }

                    # Add optional joins
                    if is_opening_join:
                        new_cover[CONF_IS_OPENING_JOIN] = is_opening_join
                    if is_closing_join:
                        new_cover[CONF_IS_CLOSING_JOIN] = is_closing_join
                    if is_closed_join:
                        new_cover[CONF_IS_CLOSED_JOIN] = is_closed_join
                    if stop_join:
                        new_cover[CONF_STOP_JOIN] = stop_join

                    if is_editing:
                        # Replace existing cover
                        updated_covers = [
                            new_cover if c.get(CONF_NAME) == old_name else c
                            for c in current_covers
                        ]
                        _LOGGER.info("Updated cover %s", name)
                    else:
                        # Append new cover
                        updated_covers = current_covers + [new_cover]
                        _LOGGER.info("Added cover %s", name)

                    # Update config entry
                    new_data = dict(self.flow.config_entry.data)
                    new_data[CONF_COVERS] = updated_covers

                    self.flow.hass.config_entries.async_update_entry(
                        self.flow.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating cover: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                CONF_NAME: self.flow._editing_join.get(CONF_NAME, ""),
                CONF_POS_JOIN: self.flow._editing_join.get(CONF_POS_JOIN, ""),
                CONF_TYPE: self.flow._editing_join.get(CONF_TYPE, "shade"),
                CONF_IS_OPENING_JOIN: self.flow._editing_join.get(CONF_IS_OPENING_JOIN, ""),
                CONF_IS_CLOSING_JOIN: self.flow._editing_join.get(CONF_IS_CLOSING_JOIN, ""),
                CONF_IS_CLOSED_JOIN: self.flow._editing_join.get(CONF_IS_CLOSED_JOIN, ""),
                CONF_STOP_JOIN: self.flow._editing_join.get(CONF_STOP_JOIN, ""),
            }

        # Show form
        add_cover_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_POS_JOIN, default=default_values.get(CONF_POS_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_TYPE, default=default_values.get(CONF_TYPE, "shade")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[{"label": "Shade", "value": "shade"}],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_IS_OPENING_JOIN, default=default_values.get(CONF_IS_OPENING_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_IS_CLOSING_JOIN, default=default_values.get(CONF_IS_CLOSING_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_IS_CLOSED_JOIN, default=default_values.get(CONF_IS_CLOSED_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_STOP_JOIN, default=default_values.get(CONF_STOP_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_cover",
            data_schema=add_cover_schema,
            errors=errors,
        )
