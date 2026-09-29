"""Climate entity configuration handler for Crestron XSIG integration."""

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_NAME, CONF_TYPE
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from ...const import (
    CONF_C1_JOIN,
    CONF_C2_JOIN,
    CONF_CLIMATES,
    CONF_COOL_SP_JOIN,
    CONF_FA_JOIN,
    CONF_FAN_AUTO_JOIN,
    CONF_FAN_MODE_AUTO_JOIN,
    CONF_FAN_MODE_ON_JOIN,
    CONF_FAN_ON_JOIN,
    CONF_FLOOR_MODE_FB_JOIN,
    # Climate joins - floor_warming
    CONF_FLOOR_MODE_JOIN,
    CONF_FLOOR_SP_FB_JOIN,
    CONF_FLOOR_SP_JOIN,
    CONF_FLOOR_TEMP_JOIN,
    CONF_H1_JOIN,
    CONF_H2_JOIN,
    # Climate joins - standard HVAC
    CONF_HEAT_SP_JOIN,
    CONF_HVAC_ACTION_COOL_JOIN,
    CONF_HVAC_ACTION_HEAT_JOIN,
    CONF_HVAC_ACTION_IDLE_JOIN,
    CONF_MODE_AUTO_JOIN,
    CONF_MODE_COOL_JOIN,
    CONF_MODE_HEAT_COOL_JOIN,
    CONF_MODE_HEAT_JOIN,
    CONF_MODE_OFF_JOIN,
    CONF_REG_TEMP_JOIN,
)

if TYPE_CHECKING:
    from ..base import BaseOptionsFlow

_LOGGER: logging.Logger = logging.getLogger(__name__)


class ClimateEntityHandler:
    """Handler for climate entity configuration."""

    def __init__(self, flow: "BaseOptionsFlow") -> None:
        """Initialize the climate entity handler.

        Args:
            flow: The options flow instance
        """
        self.flow: BaseOptionsFlow = flow

    async def async_step_select_climate_type(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Select climate type (floor_warming or standard).

        Args:
            user_input: User input data from the form, if submitted

        Returns:
            FlowResult for next step or form display
        """
        if user_input is not None:
            climate_type: str | None = user_input.get("climate_type")
            if climate_type == "floor_warming":
                return await self.flow.async_step_add_climate()
            if climate_type == "standard":
                return await self.flow.async_step_add_climate_standard()

        # Show type selection form
        type_schema: vol.Schema = vol.Schema(
            {
                vol.Required("climate_type"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Floor Warming Thermostat (5 analog joins)", "value": "floor_warming"},
                            {"label": "Standard HVAC (3 analog + 15 digital joins)", "value": "standard"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="select_climate_type",
            data_schema=type_schema,
        )

    async def async_step_add_climate(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Add or edit a climate entity (floor warming only).

        Args:
            user_input: User input data from the form, if submitted

        Returns:
            FlowResult for next step or form display
        """
        errors: dict[str, str] = {}
        is_editing: bool = self.flow._editing_join is not None

        if user_input is not None:
            try:
                name: str | None = user_input.get(CONF_NAME)
                floor_mode_join: str | None = user_input.get(CONF_FLOOR_MODE_JOIN)
                floor_mode_fb_join: str | None = user_input.get(CONF_FLOOR_MODE_FB_JOIN)
                floor_sp_join: str | None = user_input.get(CONF_FLOOR_SP_JOIN)
                floor_sp_fb_join: str | None = user_input.get(CONF_FLOOR_SP_FB_JOIN)
                floor_temp_join: str | None = user_input.get(CONF_FLOOR_TEMP_JOIN)

                # Validate all joins are analog format
                joins_to_validate: list[tuple[str, str | None]] = [
                    (CONF_FLOOR_MODE_JOIN, floor_mode_join),
                    (CONF_FLOOR_MODE_FB_JOIN, floor_mode_fb_join),
                    (CONF_FLOOR_SP_JOIN, floor_sp_join),
                    (CONF_FLOOR_SP_FB_JOIN, floor_sp_fb_join),
                    (CONF_FLOOR_TEMP_JOIN, floor_temp_join),
                ]

                for join_field, join_value in joins_to_validate:
                    if not join_value or not (join_value[0] == "a" and join_value[1:].isdigit()):
                        errors[join_field] = "invalid_join_format"

                # Check for duplicate entity name
                current_climates: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_CLIMATES, [])
                old_name: str | None = self.flow._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(c.get(CONF_NAME) == name for c in current_climates):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new climate entry (floor_warming type only)
                    new_climate: dict[str, Any] = {
                        CONF_NAME: name,
                        CONF_TYPE: "floor_warming",
                        CONF_FLOOR_MODE_JOIN: floor_mode_join,
                        CONF_FLOOR_MODE_FB_JOIN: floor_mode_fb_join,
                        CONF_FLOOR_SP_JOIN: floor_sp_join,
                        CONF_FLOOR_SP_FB_JOIN: floor_sp_fb_join,
                        CONF_FLOOR_TEMP_JOIN: floor_temp_join,
                    }

                    if is_editing:
                        # Replace existing climate
                        updated_climates: list[dict[str, Any]] = [
                            new_climate if c.get(CONF_NAME) == old_name else c for c in current_climates
                        ]
                        _LOGGER.info("Updated climate %s", name)
                    else:
                        # Append new climate
                        updated_climates: list[dict[str, Any]] = current_climates + [new_climate]
                        _LOGGER.info("Added climate %s", name)

                    # Update config entry
                    new_data: dict[str, Any] = dict(self.flow.config_entry.data)
                    new_data[CONF_CLIMATES] = updated_climates

                    self.flow.hass.config_entries.async_update_entry(self.flow.config_entry, data=new_data)

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating climate: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values: dict[str, str] = {}
        if is_editing:
            default_values = {
                CONF_NAME: self.flow._editing_join.get(CONF_NAME, ""),
                CONF_FLOOR_MODE_JOIN: self.flow._editing_join.get(CONF_FLOOR_MODE_JOIN, ""),
                CONF_FLOOR_MODE_FB_JOIN: self.flow._editing_join.get(CONF_FLOOR_MODE_FB_JOIN, ""),
                CONF_FLOOR_SP_JOIN: self.flow._editing_join.get(CONF_FLOOR_SP_JOIN, ""),
                CONF_FLOOR_SP_FB_JOIN: self.flow._editing_join.get(CONF_FLOOR_SP_FB_JOIN, ""),
                CONF_FLOOR_TEMP_JOIN: self.flow._editing_join.get(CONF_FLOOR_TEMP_JOIN, ""),
            }

        # Show form
        add_climate_schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(
                    CONF_FLOOR_MODE_JOIN, default=default_values.get(CONF_FLOOR_MODE_JOIN, "")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(
                    CONF_FLOOR_MODE_FB_JOIN, default=default_values.get(CONF_FLOOR_MODE_FB_JOIN, "")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(
                    CONF_FLOOR_SP_JOIN, default=default_values.get(CONF_FLOOR_SP_JOIN, "")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(
                    CONF_FLOOR_SP_FB_JOIN, default=default_values.get(CONF_FLOOR_SP_FB_JOIN, "")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(
                    CONF_FLOOR_TEMP_JOIN, default=default_values.get(CONF_FLOOR_TEMP_JOIN, "")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_climate",
            data_schema=add_climate_schema,
            errors=errors,
        )

    async def async_step_add_climate_standard(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Add or edit a standard HVAC climate entity.

        Args:
            user_input: User input data from the form, if submitted

        Returns:
            FlowResult for next step or form display
        """
        errors: dict[str, str] = {}
        is_editing: bool = self.flow._editing_join is not None

        if user_input is not None:
            try:
                name: str | None = user_input.get(CONF_NAME)

                # Validate analog joins (3 required)
                analog_joins: dict[str, str | None] = {
                    CONF_HEAT_SP_JOIN: user_input.get(CONF_HEAT_SP_JOIN),
                    CONF_COOL_SP_JOIN: user_input.get(CONF_COOL_SP_JOIN),
                    CONF_REG_TEMP_JOIN: user_input.get(CONF_REG_TEMP_JOIN),
                }

                for join_field, join_value in analog_joins.items():
                    if not join_value or not (join_value[0] == "a" and join_value[1:].isdigit()):
                        errors[join_field] = "invalid_join_format"

                # Validate digital joins (15 required)
                digital_joins: dict[str, str | None] = {
                    CONF_MODE_HEAT_JOIN: user_input.get(CONF_MODE_HEAT_JOIN),
                    CONF_MODE_COOL_JOIN: user_input.get(CONF_MODE_COOL_JOIN),
                    CONF_MODE_AUTO_JOIN: user_input.get(CONF_MODE_AUTO_JOIN),
                    CONF_MODE_OFF_JOIN: user_input.get(CONF_MODE_OFF_JOIN),
                    CONF_FAN_ON_JOIN: user_input.get(CONF_FAN_ON_JOIN),
                    CONF_FAN_AUTO_JOIN: user_input.get(CONF_FAN_AUTO_JOIN),
                    CONF_H1_JOIN: user_input.get(CONF_H1_JOIN),
                    CONF_C1_JOIN: user_input.get(CONF_C1_JOIN),
                    CONF_FA_JOIN: user_input.get(CONF_FA_JOIN),
                    CONF_MODE_HEAT_COOL_JOIN: user_input.get(CONF_MODE_HEAT_COOL_JOIN),
                    CONF_FAN_MODE_AUTO_JOIN: user_input.get(CONF_FAN_MODE_AUTO_JOIN),
                    CONF_FAN_MODE_ON_JOIN: user_input.get(CONF_FAN_MODE_ON_JOIN),
                    CONF_HVAC_ACTION_HEAT_JOIN: user_input.get(CONF_HVAC_ACTION_HEAT_JOIN),
                    CONF_HVAC_ACTION_COOL_JOIN: user_input.get(CONF_HVAC_ACTION_COOL_JOIN),
                    CONF_HVAC_ACTION_IDLE_JOIN: user_input.get(CONF_HVAC_ACTION_IDLE_JOIN),
                }

                for join_field, join_value in digital_joins.items():
                    if not join_value or not (join_value[0] == "d" and join_value[1:].isdigit()):
                        errors[join_field] = "invalid_join_format"

                # Validate optional digital joins (2 optional)
                h2_join: str = user_input.get(CONF_H2_JOIN, "")
                c2_join: str = user_input.get(CONF_C2_JOIN, "")

                if h2_join and not (h2_join[0] == "d" and h2_join[1:].isdigit()):
                    errors[CONF_H2_JOIN] = "invalid_join_format"
                if c2_join and not (c2_join[0] == "d" and c2_join[1:].isdigit()):
                    errors[CONF_C2_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_climates: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_CLIMATES, [])
                old_name: str | None = self.flow._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(c.get(CONF_NAME) == name for c in current_climates):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new climate entry (standard type)
                    new_climate: dict[str, Any] = {
                        CONF_NAME: name,
                        CONF_TYPE: "standard",
                        CONF_HEAT_SP_JOIN: user_input.get(CONF_HEAT_SP_JOIN),
                        CONF_COOL_SP_JOIN: user_input.get(CONF_COOL_SP_JOIN),
                        CONF_REG_TEMP_JOIN: user_input.get(CONF_REG_TEMP_JOIN),
                        CONF_MODE_HEAT_JOIN: user_input.get(CONF_MODE_HEAT_JOIN),
                        CONF_MODE_COOL_JOIN: user_input.get(CONF_MODE_COOL_JOIN),
                        CONF_MODE_AUTO_JOIN: user_input.get(CONF_MODE_AUTO_JOIN),
                        CONF_MODE_OFF_JOIN: user_input.get(CONF_MODE_OFF_JOIN),
                        CONF_FAN_ON_JOIN: user_input.get(CONF_FAN_ON_JOIN),
                        CONF_FAN_AUTO_JOIN: user_input.get(CONF_FAN_AUTO_JOIN),
                        CONF_H1_JOIN: user_input.get(CONF_H1_JOIN),
                        CONF_C1_JOIN: user_input.get(CONF_C1_JOIN),
                        CONF_FA_JOIN: user_input.get(CONF_FA_JOIN),
                        CONF_MODE_HEAT_COOL_JOIN: user_input.get(CONF_MODE_HEAT_COOL_JOIN),
                        CONF_FAN_MODE_AUTO_JOIN: user_input.get(CONF_FAN_MODE_AUTO_JOIN),
                        CONF_FAN_MODE_ON_JOIN: user_input.get(CONF_FAN_MODE_ON_JOIN),
                        CONF_HVAC_ACTION_HEAT_JOIN: user_input.get(CONF_HVAC_ACTION_HEAT_JOIN),
                        CONF_HVAC_ACTION_COOL_JOIN: user_input.get(CONF_HVAC_ACTION_COOL_JOIN),
                        CONF_HVAC_ACTION_IDLE_JOIN: user_input.get(CONF_HVAC_ACTION_IDLE_JOIN),
                    }

                    # Add optional joins if provided
                    if h2_join:
                        new_climate[CONF_H2_JOIN] = h2_join
                    if c2_join:
                        new_climate[CONF_C2_JOIN] = c2_join

                    if is_editing:
                        # Replace existing climate
                        updated_climates: list[dict[str, Any]] = [
                            new_climate if c.get(CONF_NAME) == old_name else c for c in current_climates
                        ]
                        _LOGGER.info("Updated standard climate %s", name)
                    else:
                        # Append new climate
                        updated_climates: list[dict[str, Any]] = current_climates + [new_climate]
                        _LOGGER.info("Added standard climate %s", name)

                    # Update config entry
                    new_data: dict[str, Any] = dict(self.flow.config_entry.data)
                    new_data[CONF_CLIMATES] = updated_climates

                    self.flow.hass.config_entries.async_update_entry(self.flow.config_entry, data=new_data)

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating standard climate: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values: dict[str, str] = {}
        if is_editing:
            default_values = {
                CONF_NAME: self.flow._editing_join.get(CONF_NAME, ""),
                CONF_HEAT_SP_JOIN: self.flow._editing_join.get(CONF_HEAT_SP_JOIN, ""),
                CONF_COOL_SP_JOIN: self.flow._editing_join.get(CONF_COOL_SP_JOIN, ""),
                CONF_REG_TEMP_JOIN: self.flow._editing_join.get(CONF_REG_TEMP_JOIN, ""),
                CONF_MODE_HEAT_JOIN: self.flow._editing_join.get(CONF_MODE_HEAT_JOIN, ""),
                CONF_MODE_COOL_JOIN: self.flow._editing_join.get(CONF_MODE_COOL_JOIN, ""),
                CONF_MODE_AUTO_JOIN: self.flow._editing_join.get(CONF_MODE_AUTO_JOIN, ""),
                CONF_MODE_OFF_JOIN: self.flow._editing_join.get(CONF_MODE_OFF_JOIN, ""),
                CONF_FAN_ON_JOIN: self.flow._editing_join.get(CONF_FAN_ON_JOIN, ""),
                CONF_FAN_AUTO_JOIN: self.flow._editing_join.get(CONF_FAN_AUTO_JOIN, ""),
                CONF_H1_JOIN: self.flow._editing_join.get(CONF_H1_JOIN, ""),
                CONF_H2_JOIN: self.flow._editing_join.get(CONF_H2_JOIN, ""),
                CONF_C1_JOIN: self.flow._editing_join.get(CONF_C1_JOIN, ""),
                CONF_C2_JOIN: self.flow._editing_join.get(CONF_C2_JOIN, ""),
                CONF_FA_JOIN: self.flow._editing_join.get(CONF_FA_JOIN, ""),
                CONF_MODE_HEAT_COOL_JOIN: self.flow._editing_join.get(CONF_MODE_HEAT_COOL_JOIN, ""),
                CONF_FAN_MODE_AUTO_JOIN: self.flow._editing_join.get(CONF_FAN_MODE_AUTO_JOIN, ""),
                CONF_FAN_MODE_ON_JOIN: self.flow._editing_join.get(CONF_FAN_MODE_ON_JOIN, ""),
                CONF_HVAC_ACTION_HEAT_JOIN: self.flow._editing_join.get(CONF_HVAC_ACTION_HEAT_JOIN, ""),
                CONF_HVAC_ACTION_COOL_JOIN: self.flow._editing_join.get(CONF_HVAC_ACTION_COOL_JOIN, ""),
                CONF_HVAC_ACTION_IDLE_JOIN: self.flow._editing_join.get(CONF_HVAC_ACTION_IDLE_JOIN, ""),
            }

        # Show form - organized by section
        add_climate_standard_schema: vol.Schema = vol.Schema(
            {
                # Name
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                # Temperature setpoints (3 analog)
                vol.Required(
                    CONF_HEAT_SP_JOIN, default=default_values.get(CONF_HEAT_SP_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_COOL_SP_JOIN, default=default_values.get(CONF_COOL_SP_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_REG_TEMP_JOIN, default=default_values.get(CONF_REG_TEMP_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                # HVAC modes (5 digital)
                vol.Required(
                    CONF_MODE_HEAT_JOIN, default=default_values.get(CONF_MODE_HEAT_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_MODE_COOL_JOIN, default=default_values.get(CONF_MODE_COOL_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_MODE_AUTO_JOIN, default=default_values.get(CONF_MODE_AUTO_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_MODE_HEAT_COOL_JOIN, default=default_values.get(CONF_MODE_HEAT_COOL_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_MODE_OFF_JOIN, default=default_values.get(CONF_MODE_OFF_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                # Fan modes (4 digital)
                vol.Required(CONF_FAN_ON_JOIN, default=default_values.get(CONF_FAN_ON_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(
                    CONF_FAN_AUTO_JOIN, default=default_values.get(CONF_FAN_AUTO_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_FAN_MODE_ON_JOIN, default=default_values.get(CONF_FAN_MODE_ON_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_FAN_MODE_AUTO_JOIN, default=default_values.get(CONF_FAN_MODE_AUTO_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                # HVAC equipment status (6 digital, 2 optional)
                vol.Required(CONF_H1_JOIN, default=default_values.get(CONF_H1_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_H2_JOIN, default=default_values.get(CONF_H2_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_C1_JOIN, default=default_values.get(CONF_C1_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_C2_JOIN, default=default_values.get(CONF_C2_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_FA_JOIN, default=default_values.get(CONF_FA_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                # HVAC actions (3 digital)
                vol.Required(
                    CONF_HVAC_ACTION_HEAT_JOIN, default=default_values.get(CONF_HVAC_ACTION_HEAT_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_HVAC_ACTION_COOL_JOIN, default=default_values.get(CONF_HVAC_ACTION_COOL_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
                vol.Required(
                    CONF_HVAC_ACTION_IDLE_JOIN, default=default_values.get(CONF_HVAC_ACTION_IDLE_JOIN, "")
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
            }
        )

        return self.flow.async_show_form(
            step_id="add_climate_standard",
            data_schema=add_climate_standard_schema,
            errors=errors,
        )
