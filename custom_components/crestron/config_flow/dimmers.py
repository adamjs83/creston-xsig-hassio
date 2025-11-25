"""Dimmer/keypad configuration handler for Crestron XSIG integration."""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

import voluptuous as vol
import yaml

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector, entity_registry as er, device_registry as dr

if TYPE_CHECKING:
    from ..config_flow import OptionsFlowHandler

from ..const import (
    DOMAIN,
    CONF_DIMMERS,
    CONF_BASE_JOIN,
    CONF_BUTTON_COUNT,
    CONF_HAS_LIGHTING_LOAD,
    CONF_LIGHT_BRIGHTNESS_JOIN,
    CONF_LIGHTING_LOAD,
    CONF_IS_ON_JOIN,
    CONF_BRIGHTNESS_JOIN,
    CONF_BUTTONS,
    CONF_PRESS,
    CONF_DOUBLE_PRESS,
    CONF_HOLD,
    CONF_FEEDBACK,
    CONF_ACTION,
    CONF_SERVICE_DATA,
    # For conflict checking
    CONF_TO_HUB,
    CONF_FROM_HUB,
    CONF_LIGHTS,
    CONF_SWITCHES,
    CONF_COVERS,
    CONF_POS_JOIN,
    CONF_SWITCH_JOIN,
)

_LOGGER = logging.getLogger(__name__)


class DimmerHandler:
    """Handler for dimmer/keypad configuration."""

    def __init__(self, options_flow: OptionsFlowHandler) -> None:
        """Initialize the dimmer handler.

        Args:
            options_flow: The OptionsFlowHandler instance
        """
        self.flow: OptionsFlowHandler = options_flow

    async def async_step_add_dimmer_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select dimmer join assignment mode (auto-sequential vs manual)."""
        if user_input is not None:
            mode: str | None = user_input.get("join_mode")
            if mode == "auto":
                return await self.async_step_add_dimmer_simple()
            else:  # manual
                return await self.async_step_add_dimmer_manual()

        # Show mode selection
        mode_schema: vol.Schema = vol.Schema(
            {
                vol.Required("join_mode", default="auto"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "label": "Auto-Sequential (Recommended)",
                                "value": "auto",
                            },
                            {
                                "label": "Manual (Advanced)",
                                "value": "manual",
                            },
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_dimmer_mode",
            data_schema=mode_schema,
        )

    async def async_step_add_dimmer_simple(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add dimmer/keypad - auto-sequential join assignment (v1.17.0)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                name: str = user_input.get(CONF_NAME, "").strip()
                base_join_str: str = user_input.get(CONF_BASE_JOIN, "").strip()
                button_count: int = int(user_input.get(CONF_BUTTON_COUNT, "4"))
                has_lighting: bool = user_input.get(CONF_HAS_LIGHTING_LOAD, False)
                light_brightness_join_str: str | None = user_input.get(CONF_LIGHT_BRIGHTNESS_JOIN, "").strip() if has_lighting else None

                # Validate name
                if not name:
                    errors[CONF_NAME] = "name_required"

                # Validate base join (digital format)
                if not base_join_str or not (base_join_str[0] == 'd' and base_join_str[1:].isdigit()):
                    errors[CONF_BASE_JOIN] = "invalid_join_format"
                else:
                    base_join_num: int = int(base_join_str[1:])
                    # Validate join range: need button_count * 3 sequential joins
                    max_join_needed: int = base_join_num + (button_count * 3) - 1
                    if max_join_needed > 4096:
                        errors[CONF_BASE_JOIN] = "join_range_exceeded"

                # Validate lighting load brightness join if provided
                if has_lighting:
                    if not light_brightness_join_str or not (light_brightness_join_str[0] == 'a' and light_brightness_join_str[1:].isdigit()):
                        errors[CONF_LIGHT_BRIGHTNESS_JOIN] = "invalid_join_format"

                # Check for join conflicts
                if not errors:
                    joins_to_check: list[str] = []

                    # Add button joins (press, double, hold for each button)
                    for i in range(button_count):
                        offset: int = i * 3
                        joins_to_check.append(f"d{base_join_num + offset}")  # press
                        joins_to_check.append(f"d{base_join_num + offset + 1}")  # double
                        joins_to_check.append(f"d{base_join_num + offset + 2}")  # hold

                    # Add lighting load brightness join
                    if has_lighting and light_brightness_join_str:
                        joins_to_check.append(light_brightness_join_str)

                    conflict: str | None = self._check_join_conflicts(joins_to_check)
                    if conflict:
                        errors["base"] = "join_conflict"

                if not errors:
                    # Build dimmer config
                    dimmer_config: dict[str, Any] = {
                        CONF_NAME: name,
                        CONF_BASE_JOIN: base_join_str,
                        CONF_BUTTON_COUNT: button_count,
                    }

                    if has_lighting and light_brightness_join_str:
                        dimmer_config[CONF_HAS_LIGHTING_LOAD] = True
                        dimmer_config[CONF_LIGHT_BRIGHTNESS_JOIN] = light_brightness_join_str

                    # Save dimmer - get fresh entry to preserve LED bindings
                    fresh_entry: Any = self.flow.hass.config_entries.async_get_entry(self.flow.config_entry.entry_id)
                    if not fresh_entry:
                        _LOGGER.error("Config entry not found, cannot save dimmer")
                        errors["base"] = "entry_not_found"
                    else:
                        current_dimmers: list[dict[str, Any]] = fresh_entry.data.get(CONF_DIMMERS, []).copy()
                        current_dimmers.append(dimmer_config)

                        new_data: dict[str, Any] = dict(fresh_entry.data)
                        new_data[CONF_DIMMERS] = current_dimmers
                        self.flow.hass.config_entries.async_update_entry(
                            fresh_entry, data=new_data
                        )

                    _LOGGER.info(
                        "Added dimmer '%s' with %d buttons (base join: %s)",
                        name, button_count, base_join_str
                    )

                    # Reload integration
                    await self.flow._async_reload_integration()

                    # Return to dimmer menu
                    return await self.flow.async_step_dimmer_menu()

            except Exception as ex:
                _LOGGER.exception("Unexpected error adding dimmer: %s", ex)
                errors["base"] = "unknown"

        # Show form
        dimmer_schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_NAME): selector.TextSelector(),
                vol.Required(CONF_BASE_JOIN): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_BUTTON_COUNT, default="4"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "2 Buttons", "value": "2"},
                            {"label": "3 Buttons", "value": "3"},
                            {"label": "4 Buttons", "value": "4"},
                            {"label": "5 Buttons", "value": "5"},
                            {"label": "6 Buttons", "value": "6"},
                        ],
                    )
                ),
                vol.Optional(CONF_HAS_LIGHTING_LOAD, default=False): selector.BooleanSelector(),
                vol.Optional(CONF_LIGHT_BRIGHTNESS_JOIN): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_dimmer_simple",
            data_schema=dimmer_schema,
            errors=errors,
        )

    async def async_step_add_dimmer_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add dimmer/keypad - manual join assignment (v1.17.1)."""
        errors: dict[str, str] = {}

        # Store button count in editing state for form generation
        if user_input and "button_count" in user_input and not hasattr(self.flow, "_dimmer_button_count"):
            self.flow._dimmer_button_count: int = int(user_input.get("button_count", "4"))

        if user_input is not None and hasattr(self.flow, "_dimmer_button_count"):
            try:
                name: str = user_input.get(CONF_NAME, "").strip()
                button_count: int = self.flow._dimmer_button_count
                has_lighting: bool = user_input.get(CONF_HAS_LIGHTING_LOAD, False)
                light_brightness_join_str: str | None = user_input.get(CONF_LIGHT_BRIGHTNESS_JOIN, "").strip() if has_lighting else None

                # Validate name
                if not name:
                    errors[CONF_NAME] = "name_required"

                # Collect and validate button joins
                button_joins: dict[int, dict[str, str]] = {}
                joins_to_check: list[str] = []

                for btn_num in range(1, button_count + 1):
                    press_join: str = user_input.get(f"button_{btn_num}_press", "").strip()
                    double_join: str = user_input.get(f"button_{btn_num}_double", "").strip()
                    hold_join: str = user_input.get(f"button_{btn_num}_hold", "").strip()

                    # Validate press join (required)
                    if not press_join or not (press_join[0] == 'd' and press_join[1:].isdigit()):
                        errors[f"button_{btn_num}_press"] = "invalid_join_format"
                    else:
                        joins_to_check.append(press_join)
                        button_joins[btn_num] = {"press": press_join}

                    # Validate double join (required)
                    if not double_join or not (double_join[0] == 'd' and double_join[1:].isdigit()):
                        errors[f"button_{btn_num}_double"] = "invalid_join_format"
                    else:
                        joins_to_check.append(double_join)
                        if btn_num in button_joins:
                            button_joins[btn_num]["double"] = double_join

                    # Validate hold join (required)
                    if not hold_join or not (hold_join[0] == 'd' and hold_join[1:].isdigit()):
                        errors[f"button_{btn_num}_hold"] = "invalid_join_format"
                    else:
                        joins_to_check.append(hold_join)
                        if btn_num in button_joins:
                            button_joins[btn_num]["hold"] = hold_join

                # Validate lighting load brightness join if provided
                if has_lighting:
                    if not light_brightness_join_str or not (light_brightness_join_str[0] == 'a' and light_brightness_join_str[1:].isdigit()):
                        errors[CONF_LIGHT_BRIGHTNESS_JOIN] = "invalid_join_format"
                    else:
                        joins_to_check.append(light_brightness_join_str)

                # Check for join conflicts
                if not errors:
                    conflict: str | None = self._check_join_conflicts(joins_to_check)
                    if conflict:
                        errors["base"] = "join_conflict"

                if not errors:
                    # Build dimmer config
                    dimmer_config: dict[str, Any] = {
                        CONF_NAME: name,
                        CONF_BUTTON_COUNT: button_count,
                        "manual_joins": button_joins,  # Store manual join mapping
                    }

                    if has_lighting and light_brightness_join_str:
                        dimmer_config[CONF_HAS_LIGHTING_LOAD] = True
                        dimmer_config[CONF_LIGHT_BRIGHTNESS_JOIN] = light_brightness_join_str

                    # Save dimmer - get fresh entry to preserve LED bindings
                    fresh_entry: Any = self.flow.hass.config_entries.async_get_entry(self.flow.config_entry.entry_id)
                    if not fresh_entry:
                        _LOGGER.error("Config entry not found, cannot save dimmer")
                        errors["base"] = "entry_not_found"
                    else:
                        current_dimmers: list[dict[str, Any]] = fresh_entry.data.get(CONF_DIMMERS, []).copy()
                        current_dimmers.append(dimmer_config)

                        new_data: dict[str, Any] = dict(fresh_entry.data)
                        new_data[CONF_DIMMERS] = current_dimmers
                        self.flow.hass.config_entries.async_update_entry(
                            fresh_entry, data=new_data
                        )

                    _LOGGER.info(
                        "Added dimmer '%s' with %d buttons (manual joins)",
                        name, button_count
                    )

                    # Clear temp state
                    delattr(self.flow, "_dimmer_button_count")

                    # Reload integration
                    await self.flow._async_reload_integration()

                    # Return to dimmer menu
                    return await self.flow.async_step_dimmer_menu()

            except Exception as ex:
                _LOGGER.exception("Unexpected error adding dimmer (manual): %s", ex)
                errors["base"] = "unknown"

        # Build dynamic form based on button count
        button_count: int = getattr(self.flow, "_dimmer_button_count", int(user_input.get(CONF_BUTTON_COUNT, "4")) if user_input else 4)

        # Build schema fields
        schema_fields: dict[Any, Any] = {
            vol.Required(CONF_NAME): selector.TextSelector(),
            vol.Required(CONF_BUTTON_COUNT, default=str(button_count)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"label": "2 Buttons", "value": "2"},
                        {"label": "3 Buttons", "value": "3"},
                        {"label": "4 Buttons", "value": "4"},
                        {"label": "5 Buttons", "value": "5"},
                        {"label": "6 Buttons", "value": "6"},
                    ],
                )
            ),
        }

        # Add button join fields dynamically
        for btn_num in range(1, button_count + 1):
            schema_fields[vol.Required(f"button_{btn_num}_press")] = selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            )
            schema_fields[vol.Required(f"button_{btn_num}_double")] = selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            )
            schema_fields[vol.Required(f"button_{btn_num}_hold")] = selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            )

        # Add lighting load fields
        schema_fields[vol.Optional(CONF_HAS_LIGHTING_LOAD, default=False)] = selector.BooleanSelector()
        schema_fields[vol.Optional(CONF_LIGHT_BRIGHTNESS_JOIN)] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        )

        dimmer_schema: vol.Schema = vol.Schema(schema_fields)

        return self.flow.async_show_form(
            step_id="add_dimmer_manual",
            data_schema=dimmer_schema,
            errors=errors,
        )

    async def async_step_add_dimmer_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Basic dimmer information."""
        _LOGGER.debug("async_step_add_dimmer_basic called with user_input: %s", user_input)
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                name: str = user_input.get(CONF_NAME, "").strip()
                button_count: int = int(user_input.get(CONF_BUTTON_COUNT, "4"))  # Convert string to int
                has_lighting_load: bool = user_input.get("has_lighting_load", False)

                # Validate name
                if not name:
                    errors[CONF_NAME] = "name_required"

                # Check for duplicate dimmer name
                current_dimmers: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_DIMMERS, [])
                if any(d.get(CONF_NAME) == name for d in current_dimmers):
                    errors[CONF_NAME] = "dimmer_name_exists"

                if not errors:
                    # Store temporary dimmer config
                    self.flow._editing_join = {
                        CONF_NAME: name,
                        CONF_BUTTON_COUNT: button_count,
                        "has_lighting_load": has_lighting_load,
                        CONF_BUTTONS: [],
                    }

                    if has_lighting_load:
                        return await self.async_step_add_dimmer_lighting()
                    else:
                        # Skip lighting, go to button 1
                        return await self.async_step_add_dimmer_button(button_num=1)

            except Exception as ex:
                _LOGGER.exception("Unexpected error adding dimmer: %s", ex)
                errors["base"] = "unknown"

        # Show basic info form
        basic_schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_NAME): selector.TextSelector(),
                vol.Required(CONF_BUTTON_COUNT, default="4"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "2 Buttons", "value": "2"},
                            {"label": "3 Buttons", "value": "3"},
                            {"label": "4 Buttons", "value": "4"},
                            {"label": "5 Buttons", "value": "5"},
                            {"label": "6 Buttons", "value": "6"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("has_lighting_load", default=False): selector.BooleanSelector(),
            }
        )

        return self.flow.async_show_form(
            step_id="add_dimmer_basic",
            data_schema=basic_schema,
            errors=errors,
            description_placeholders={"step": "1"},
        )

    async def async_step_add_dimmer_lighting(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Configure lighting load (optional)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                light_name: str = user_input.get("light_name", "").strip()
                is_on_join: str = user_input.get(CONF_IS_ON_JOIN, "").strip()
                has_brightness: bool = user_input.get("has_brightness", False)
                brightness_join: str = user_input.get(CONF_BRIGHTNESS_JOIN, "").strip()

                # Validate light name
                if not light_name:
                    errors["light_name"] = "name_required"

                # Validate is_on_join format
                if not is_on_join or not (is_on_join[0] == 'd' and is_on_join[1:].isdigit()):
                    errors[CONF_IS_ON_JOIN] = "invalid_join_format"

                # Validate brightness join if enabled
                if has_brightness:
                    if not brightness_join or not (brightness_join[0] == 'a' and brightness_join[1:].isdigit()):
                        errors[CONF_BRIGHTNESS_JOIN] = "invalid_join_format"

                # Check for join conflicts
                if not errors:
                    all_joins: list[str] = [is_on_join]
                    if has_brightness and brightness_join:
                        all_joins.append(brightness_join)

                    conflict: str | None = self._check_join_conflicts(all_joins)
                    if conflict:
                        errors["base"] = f"join_conflict_{conflict}"

                if not errors:
                    # Store lighting load config
                    lighting_load: dict[str, str] = {
                        CONF_NAME: light_name,
                        CONF_IS_ON_JOIN: is_on_join,
                    }
                    if has_brightness and brightness_join:
                        lighting_load[CONF_BRIGHTNESS_JOIN] = brightness_join

                    self.flow._editing_join[CONF_LIGHTING_LOAD] = lighting_load

                    # Move to button 1
                    return await self.async_step_add_dimmer_button(button_num=1)

            except Exception as ex:
                _LOGGER.exception("Unexpected error configuring lighting load: %s", ex)
                errors["base"] = "unknown"

        # Show lighting load form
        lighting_schema: vol.Schema = vol.Schema(
            {
                vol.Required("light_name"): selector.TextSelector(),
                vol.Required(CONF_IS_ON_JOIN): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional("has_brightness", default=False): selector.BooleanSelector(),
                vol.Optional(CONF_BRIGHTNESS_JOIN): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_dimmer_lighting",
            data_schema=lighting_schema,
            errors=errors,
            description_placeholders={
                "dimmer_name": self.flow._editing_join.get(CONF_NAME, ""),
                "step": "2",
            },
        )

    async def async_step_add_dimmer_button(
        self, user_input: dict[str, Any] | None = None, button_num: int = 1
    ) -> FlowResult:
        """Configure a single button (dynamic, handles buttons 1-6)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Parse button configuration
                button_config: dict[str, Any] = {"number": button_num}

                # Press action
                config_press: bool = user_input.get("config_press", False)
                press_join: str = user_input.get("press_join", "").strip()
                press_entity: str | None = user_input.get("press_entity")
                press_action: str | None = user_input.get("press_action")
                press_data: str = user_input.get("press_service_data", "").strip()

                # Double press action
                config_double: bool = user_input.get("config_double_press", False)
                double_join: str = user_input.get("double_press_join", "").strip()
                double_entity: str | None = user_input.get("double_press_entity")
                double_action: str | None = user_input.get("double_press_action")
                double_data: str = user_input.get("double_service_data", "").strip()

                # Hold action
                config_hold: bool = user_input.get("config_hold", False)
                hold_join: str = user_input.get("hold_join", "").strip()
                hold_entity: str | None = user_input.get("hold_entity")
                hold_action: str | None = user_input.get("hold_action")
                hold_data: str = user_input.get("hold_service_data", "").strip()

                # Feedback
                config_feedback: bool = user_input.get("config_feedback", False)
                feedback_join: str = user_input.get("feedback_join", "").strip()
                feedback_entity: str | None = user_input.get("feedback_entity")

                # Validate press
                if config_press:
                    if not press_join or not (press_join[0] == 'd' and press_join[1:].isdigit()):
                        errors["press_join"] = "invalid_join_format"
                    elif not press_entity or not press_action:
                        errors["press_entity"] = "entity_and_action_required"
                    else:
                        button_config[CONF_PRESS] = {
                            "join": press_join,
                            "entity_id": press_entity,
                            CONF_ACTION: press_action,
                        }
                        if press_data:
                            try:
                                button_config[CONF_PRESS][CONF_SERVICE_DATA] = yaml.safe_load(press_data)
                            except yaml.YAMLError:
                                errors["press_service_data"] = "invalid_yaml"

                # Validate double press
                if config_double:
                    if not double_join or not (double_join[0] == 'd' and double_join[1:].isdigit()):
                        errors["double_press_join"] = "invalid_join_format"
                    elif not double_entity or not double_action:
                        errors["double_press_entity"] = "entity_and_action_required"
                    else:
                        button_config[CONF_DOUBLE_PRESS] = {
                            "join": double_join,
                            "entity_id": double_entity,
                            CONF_ACTION: double_action,
                        }
                        if double_data:
                            try:
                                button_config[CONF_DOUBLE_PRESS][CONF_SERVICE_DATA] = yaml.safe_load(double_data)
                            except yaml.YAMLError:
                                errors["double_service_data"] = "invalid_yaml"

                # Validate hold
                if config_hold:
                    if not hold_join or not (hold_join[0] == 'd' and hold_join[1:].isdigit()):
                        errors["hold_join"] = "invalid_join_format"
                    elif not hold_entity or not hold_action:
                        errors["hold_entity"] = "entity_and_action_required"
                    else:
                        button_config[CONF_HOLD] = {
                            "join": hold_join,
                            "entity_id": hold_entity,
                            CONF_ACTION: hold_action,
                        }
                        if hold_data:
                            try:
                                button_config[CONF_HOLD][CONF_SERVICE_DATA] = yaml.safe_load(hold_data)
                            except yaml.YAMLError:
                                errors["hold_service_data"] = "invalid_yaml"

                # Validate feedback
                if config_feedback:
                    if not feedback_join or not (feedback_join[0] == 'd' and feedback_join[1:].isdigit()):
                        errors["feedback_join"] = "invalid_join_format"
                    elif not feedback_entity:
                        errors["feedback_entity"] = "entity_required"
                    else:
                        button_config[CONF_FEEDBACK] = {
                            "join": feedback_join,
                            "entity_id": feedback_entity,
                        }

                # Check for join conflicts
                if not errors:
                    button_joins: list[str] = []
                    if CONF_PRESS in button_config:
                        button_joins.append(button_config[CONF_PRESS]["join"])
                    if CONF_DOUBLE_PRESS in button_config:
                        button_joins.append(button_config[CONF_DOUBLE_PRESS]["join"])
                    if CONF_HOLD in button_config:
                        button_joins.append(button_config[CONF_HOLD]["join"])
                    if CONF_FEEDBACK in button_config:
                        button_joins.append(button_config[CONF_FEEDBACK]["join"])

                    conflict: str | None = self._check_join_conflicts(button_joins)
                    if conflict:
                        errors["base"] = f"join_conflict"

                if not errors:
                    # Add button to dimmer config
                    self.flow._editing_join[CONF_BUTTONS].append(button_config)

                    # Check if we need more buttons
                    total_buttons: int = self.flow._editing_join.get(CONF_BUTTON_COUNT, 0)
                    if button_num < total_buttons:
                        # More buttons to configure
                        return await self.async_step_add_dimmer_button(button_num=button_num + 1)
                    else:
                        # All buttons configured, save dimmer
                        return await self._save_dimmer()

            except Exception as ex:
                _LOGGER.exception("Unexpected error configuring button %s: %s", button_num, ex)
                errors["base"] = "unknown"

        # Build dynamic form for this button
        total_buttons: int = self.flow._editing_join.get(CONF_BUTTON_COUNT, 0)

        button_schema: vol.Schema = vol.Schema(
            {
                # Press action
                vol.Optional("config_press", default=False): selector.BooleanSelector(),
                vol.Optional("press_join"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional("press_entity"): selector.EntitySelector(),
                vol.Optional("press_action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["turn_on", "turn_off", "toggle"],  # Will be dynamic based on entity
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("press_service_data"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),

                # Double press action
                vol.Optional("config_double_press", default=False): selector.BooleanSelector(),
                vol.Optional("double_press_join"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional("double_press_entity"): selector.EntitySelector(),
                vol.Optional("double_press_action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["turn_on", "turn_off", "toggle"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("double_service_data"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),

                # Hold action
                vol.Optional("config_hold", default=False): selector.BooleanSelector(),
                vol.Optional("hold_join"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional("hold_entity"): selector.EntitySelector(),
                vol.Optional("hold_action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["turn_on", "turn_off", "toggle"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("hold_service_data"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),

                # Feedback
                vol.Optional("config_feedback", default=False): selector.BooleanSelector(),
                vol.Optional("feedback_join"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional("feedback_entity"): selector.EntitySelector(),
            }
        )

        return self.flow.async_show_form(
            step_id="add_dimmer_button",
            data_schema=button_schema,
            errors=errors,
            description_placeholders={
                "dimmer_name": self.flow._editing_join.get(CONF_NAME, ""),
                "button_num": str(button_num),
                "total_buttons": str(total_buttons),
                "step": str(2 + button_num if self.flow._editing_join.get(CONF_LIGHTING_LOAD) else 1 + button_num),
            },
        )

    async def _save_dimmer(self) -> FlowResult:
        """Save the dimmer configuration."""
        try:
            # Get fresh entry to preserve LED bindings
            fresh_entry: Any = self.flow.hass.config_entries.async_get_entry(self.flow.config_entry.entry_id)
            if not fresh_entry:
                _LOGGER.error("Config entry not found, cannot save dimmer")
                return self.flow.async_abort(reason="entry_not_found")

            current_dimmers: list[dict[str, Any]] = fresh_entry.data.get(CONF_DIMMERS, []).copy()
            current_dimmers.append(self.flow._editing_join)

            # Update config entry with fresh data
            new_data: dict[str, Any] = dict(fresh_entry.data)
            new_data[CONF_DIMMERS] = current_dimmers
            self.flow.hass.config_entries.async_update_entry(
                fresh_entry, data=new_data
            )

            _LOGGER.info(
                "Added dimmer '%s' with %s buttons",
                self.flow._editing_join.get(CONF_NAME),
                self.flow._editing_join.get(CONF_BUTTON_COUNT),
            )

            # Clear editing state
            self.flow._editing_join = None

            # Reload integration
            await self.flow._async_reload_integration()

            return self.flow.async_create_entry(title="", data={})

        except Exception as ex:
            _LOGGER.exception("Failed to save dimmer: %s", ex)
            return self.flow.async_abort(reason="save_failed")

    async def async_step_select_dimmer_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which dimmer to edit."""
        current_dimmers: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_DIMMERS, [])

        if not current_dimmers:
            return self.flow.async_abort(reason="no_dimmers_configured")

        if user_input is not None:
            dimmer_name: str | None = user_input.get("dimmer_to_edit")

            # Find the dimmer
            dimmer: dict[str, Any] | None = next((d for d in current_dimmers if d.get(CONF_NAME) == dimmer_name), None)
            if dimmer:
                self.flow._editing_join = dimmer.copy()
                return await self.async_step_edit_dimmer()

        # Build dimmer selection
        dimmer_options: list[dict[str, str]] = [
            {"label": f"{d.get(CONF_NAME)} ({d.get(CONF_BUTTON_COUNT)} buttons)", "value": d.get(CONF_NAME)}
            for d in current_dimmers
        ]

        select_schema: vol.Schema = vol.Schema(
            {
                vol.Required("dimmer_to_edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=dimmer_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="select_dimmer_to_edit",
            data_schema=select_schema,
        )

    async def async_step_edit_dimmer(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit an existing dimmer (full reconfiguration)."""
        if user_input is not None:
            next_step: str | None = user_input.get("action")
            if next_step == "reconfigure":
                # User chose to reconfigure
                # Start from beginning with current config pre-filled
                return await self.async_step_add_dimmer_basic()
            elif next_step == "back":
                # Go back to dimmer selection
                self.flow._editing_join = None
                return await self.flow.async_step_select_dimmer_to_edit()

        # Show edit dimmer menu
        dimmer_name: str = self.flow._editing_join.get(CONF_NAME, "")
        button_count: int = self.flow._editing_join.get(CONF_BUTTON_COUNT, 0)

        menu_schema: vol.Schema = vol.Schema(
            {
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Reconfigure Dimmer/Keypad", "value": "reconfigure"},
                            {"label": "← Back", "value": "back"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="edit_dimmer",
            data_schema=menu_schema,
            description_placeholders={
                "dimmer_name": dimmer_name,
                "button_count": str(button_count),
            },
        )

    async def async_step_remove_dimmers(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove selected dimmers."""
        errors: dict[str, str] = {}
        current_dimmers: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_DIMMERS, [])

        if not current_dimmers:
            return self.flow.async_abort(reason="no_dimmers_configured")

        if user_input is not None:
            try:
                dimmers_to_remove: list[str] = user_input.get("dimmers_to_remove", [])

                if dimmers_to_remove:
                    # Get fresh entry to preserve LED bindings
                    fresh_entry: Any = self.flow.hass.config_entries.async_get_entry(self.flow.config_entry.entry_id)
                    if not fresh_entry:
                        _LOGGER.error("Config entry not found, cannot remove dimmers")
                        errors["base"] = "entry_not_found"
                    else:
                        # Filter out removed dimmers
                        updated_dimmers: list[dict[str, Any]] = [
                            d for d in current_dimmers
                            if d.get(CONF_NAME) not in dimmers_to_remove
                        ]

                        # Update config entry with fresh data
                        new_data: dict[str, Any] = dict(fresh_entry.data)
                        new_data[CONF_DIMMERS] = updated_dimmers
                        self.flow.hass.config_entries.async_update_entry(
                            fresh_entry, data=new_data
                        )

                        # Clean up entities generated by these dimmers
                        for dimmer_name in dimmers_to_remove:
                            dimmer: dict[str, Any] | None = next((d for d in current_dimmers if d.get(CONF_NAME) == dimmer_name), None)
                            if dimmer:
                                # Remove all entities and device from registry
                                await self._cleanup_dimmer_entities(dimmer)

                        _LOGGER.info("Removed %s dimmer(s)", len(dimmers_to_remove))

                        # Reload integration
                        await self.flow._async_reload_integration()

                if not errors:
                    return self.flow.async_create_entry(title="", data={})

            except Exception as ex:
                _LOGGER.exception("Unexpected error removing dimmers: %s", ex)
                errors["base"] = "unknown"

        # Build dimmer options
        dimmer_options: list[dict[str, str]] = [
            {"label": f"{d.get(CONF_NAME)} ({d.get(CONF_BUTTON_COUNT)} buttons)", "value": d.get(CONF_NAME)}
            for d in current_dimmers
        ]

        # Show removal form
        remove_schema: vol.Schema = vol.Schema(
            {
                vol.Optional("dimmers_to_remove"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=dimmer_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=True,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="remove_dimmers",
            data_schema=remove_schema,
            errors=errors,
        )

    def _check_join_conflicts(self, new_joins: list[str]) -> str | None:
        """Check if any joins conflict with existing configuration."""
        # Check against all existing joins (to_joins, from_joins, entities, other dimmers)
        current_to_joins: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_FROM_HUB, [])
        current_lights: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_LIGHTS, [])
        current_switches: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_SWITCHES, [])
        current_covers: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_COVERS, [])
        current_dimmers: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_DIMMERS, [])

        used_joins: set[str] = set()

        # Collect all used joins
        for tj in current_to_joins:
            used_joins.add(tj.get("join"))
        for fj in current_from_joins:
            used_joins.add(fj.get("join"))
        for light in current_lights:
            used_joins.add(light.get(CONF_IS_ON_JOIN))
            if light.get(CONF_BRIGHTNESS_JOIN):
                used_joins.add(light.get(CONF_BRIGHTNESS_JOIN))
        for switch in current_switches:
            used_joins.add(switch.get(CONF_SWITCH_JOIN))
        for cover in current_covers:
            used_joins.add(cover.get(CONF_POS_JOIN))
        # Add dimmer joins...
        for dimmer in current_dimmers:
            if dimmer.get(CONF_LIGHTING_LOAD):
                ll = dimmer[CONF_LIGHTING_LOAD]
                used_joins.add(ll.get(CONF_IS_ON_JOIN))
                if ll.get(CONF_BRIGHTNESS_JOIN):
                    used_joins.add(ll.get(CONF_BRIGHTNESS_JOIN))
            for button in dimmer.get(CONF_BUTTONS, []):
                for action_type in [CONF_PRESS, CONF_DOUBLE_PRESS, CONF_HOLD, CONF_FEEDBACK]:
                    if button.get(action_type):
                        used_joins.add(button[action_type].get("join"))

        # Check for conflicts
        for join in new_joins:
            if join in used_joins:
                return join

        # Check for duplicates within new_joins
        if len(new_joins) != len(set(new_joins)):
            return "duplicate_in_list"

        return None

    async def _cleanup_dimmer_entities(self, dimmer: dict[str, Any]) -> None:
        """Remove entities created by a dimmer from entity and device registry."""
        entity_reg: er.EntityRegistry = er.async_get(self.flow.hass)
        device_reg: dr.DeviceRegistry = dr.async_get(self.flow.hass)

        dimmer_name: str = dimmer.get(CONF_NAME)
        button_count: int = dimmer.get(CONF_BUTTON_COUNT, 2)
        base_join: str | None = dimmer.get(CONF_BASE_JOIN)
        # Note: JSON serialization converts int keys to strings
        manual_joins: dict[str, dict[str, str]] | None = dimmer.get("manual_joins")

        _LOGGER.debug("Cleaning up dimmer '%s' with %d buttons", dimmer_name, button_count)

        # Remove event entities (one per button)
        for button_num in range(1, button_count + 1):
            unique_id: str = f"crestron_event_{dimmer_name}_button_{button_num}"
            entity_id: str | None = entity_reg.async_get_entity_id("event", DOMAIN, unique_id)
            if entity_id:
                _LOGGER.debug("Removing event entity: %s", entity_id)
                entity_reg.async_remove(entity_id)

            # Remove select entity (LED binding, one per button)
            unique_id = f"crestron_led_binding_{dimmer_name}_button_{button_num}"
            entity_id = entity_reg.async_get_entity_id("select", DOMAIN, unique_id)
            if entity_id:
                _LOGGER.debug("Removing select entity: %s", entity_id)
                entity_reg.async_remove(entity_id)

            # Remove LED switch entity (one per button)
            # Calculate the press join for this button
            btn_key: str = str(button_num)
            if manual_joins and btn_key in manual_joins:
                press_join_str: str = manual_joins[btn_key]["press"]
                press_join: int = int(press_join_str[1:])
            else:
                # Auto-sequential mode
                base_offset: int = (button_num - 1) * 3
                press_join: int = int(base_join[1:]) + base_offset

            unique_id: str = f"crestron_led_{dimmer_name}_d{press_join}"
            entity_id: str | None = entity_reg.async_get_entity_id("switch", DOMAIN, unique_id)
            if entity_id:
                _LOGGER.debug("Removing LED switch entity: %s", entity_id)
                entity_reg.async_remove(entity_id)

        # Remove lighting load entity if present
        if dimmer.get(CONF_HAS_LIGHTING_LOAD):
            brightness_join_str: str | None = dimmer.get(CONF_LIGHT_BRIGHTNESS_JOIN)
            if brightness_join_str:
                brightness_join: int = int(brightness_join_str[1:])  # Remove 'a' prefix
                unique_id: str = f"crestron_light_dimmer_{dimmer_name}_a{brightness_join}"
                entity_id: str | None = entity_reg.async_get_entity_id("light", DOMAIN, unique_id)
                if entity_id:
                    _LOGGER.debug("Removing dimmer light entity: %s", entity_id)
                    entity_reg.async_remove(entity_id)

        # Remove the device from device registry
        device_identifier: tuple[str, str] = (DOMAIN, f"dimmer_{dimmer_name}")
        device: dr.DeviceEntry | None = device_reg.async_get_device(identifiers={device_identifier})
        if device:
            _LOGGER.debug("Removing device: %s", dimmer_name)
            device_reg.async_remove_device(device.id)
