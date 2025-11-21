"""Menu navigation handlers for Crestron XSIG config flow."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from ..const import (
    CONF_COVERS,
    CONF_BINARY_SENSORS,
    CONF_SENSORS,
    CONF_LIGHTS,
    CONF_SWITCHES,
    CONF_CLIMATES,
    CONF_DIMMERS,
    CONF_MEDIA_PLAYERS,
    CONF_TO_HUB,
    CONF_FROM_HUB,
)

_LOGGER = logging.getLogger(__name__)


class MenuHandler:
    """Handles menu navigation for options flow."""

    def __init__(self, options_flow):
        """Initialize menu handler.

        Args:
            options_flow: The OptionsFlowHandler instance
        """
        self.flow = options_flow

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Main menu - choose between entity, join sync, or dimmer/keypad management."""
        if user_input is not None:
            next_step = user_input.get("action")
            if next_step == "entity_menu":
                return await self.flow.async_step_entity_menu()
            elif next_step == "join_menu":
                return await self.flow.async_step_join_menu()
            elif next_step == "dimmer_menu":
                return await self.flow.async_step_dimmer_menu()
            else:
                # Done
                return self.flow.async_create_entry(title="", data={})

        # Get current counts for display
        current_covers = self.flow.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.flow.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.flow.config_entry.data.get(CONF_SENSORS, [])
        current_lights = self.flow.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.flow.config_entry.data.get(CONF_SWITCHES, [])
        current_climates = self.flow.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.flow.config_entry.data.get(CONF_MEDIA_PLAYERS, [])
        total_entities = len(current_covers) + len(current_binary_sensors) + len(current_sensors) + len(current_lights) + len(current_switches) + len(current_climates) + len(current_media_players)

        current_to_joins = self.flow.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.flow.config_entry.data.get(CONF_FROM_HUB, [])
        total_joins = len(current_to_joins) + len(current_from_joins)

        current_dimmers = self.flow.config_entry.data.get(CONF_DIMMERS, [])
        total_dimmers = len(current_dimmers)

        # Show main menu
        menu_schema = vol.Schema(
            {
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": f"Manage Entities ({total_entities} configured)", "value": "entity_menu"},
                            {"label": f"Manage Join Syncs ({total_joins} configured)", "value": "join_menu"},
                            {"label": f"Manage Dimmers/Keypads ({total_dimmers} configured)", "value": "dimmer_menu"},
                            {"label": "Done", "value": "done"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="init",
            data_schema=menu_schema,
            description_placeholders={
                "entities": str(total_entities),
                "joins": str(total_joins),
                "dimmers": str(total_dimmers),
            },
        )

    async def async_step_entity_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Entity management submenu."""
        if user_input is not None:
            next_step = user_input.get("action")
            if next_step == "add_entity":
                return await self.flow.async_step_select_entity_type()
            elif next_step == "edit_entities":
                return await self.flow.async_step_select_entity_to_edit()
            elif next_step == "remove_entities":
                return await self.flow.async_step_remove_entities()
            elif next_step == "back":
                return await self.flow.async_step_init()

        # Get current entity counts
        current_covers = self.flow.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.flow.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.flow.config_entry.data.get(CONF_SENSORS, [])
        current_lights = self.flow.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.flow.config_entry.data.get(CONF_SWITCHES, [])
        current_climates = self.flow.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.flow.config_entry.data.get(CONF_MEDIA_PLAYERS, [])
        total_entities = len(current_covers) + len(current_binary_sensors) + len(current_sensors) + len(current_lights) + len(current_switches) + len(current_climates) + len(current_media_players)

        # Show entity menu
        menu_schema = vol.Schema(
            {
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Add Entity", "value": "add_entity"},
                            {"label": f"Edit Entity ({total_entities} available)", "value": "edit_entities"},
                            {"label": f"Remove Entity ({total_entities} available)", "value": "remove_entities"},
                            {"label": "← Back to Main Menu", "value": "back"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="entity_menu",
            data_schema=menu_schema,
        )

    async def async_step_select_entity_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which type of entity to add."""
        if user_input is not None:
            self.flow._editing_join = None  # Clear editing state
            entity_type = user_input.get("entity_type")
            if entity_type == "light":
                return await self.flow.async_step_add_light()
            elif entity_type == "switch":
                return await self.flow.async_step_add_switch()
            elif entity_type == "cover":
                return await self.flow.async_step_add_cover()
            elif entity_type == "binary_sensor":
                return await self.flow.async_step_add_binary_sensor()
            elif entity_type == "sensor":
                return await self.flow.async_step_add_sensor()
            elif entity_type == "climate":
                return await self.flow.async_step_select_climate_type()
            elif entity_type == "media_player":
                return await self.flow.async_step_add_media_player()
            elif entity_type == "back":
                return await self.flow.async_step_entity_menu()

        # Get current counts
        current_lights = self.flow.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.flow.config_entry.data.get(CONF_SWITCHES, [])
        current_covers = self.flow.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.flow.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.flow.config_entry.data.get(CONF_SENSORS, [])
        current_climates = self.flow.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.flow.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

        # Show entity type selection
        menu_schema = vol.Schema(
            {
                vol.Required("entity_type"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": f"Light ({len(current_lights)} configured)", "value": "light"},
                            {"label": f"Switch ({len(current_switches)} configured)", "value": "switch"},
                            {"label": f"Cover ({len(current_covers)} configured)", "value": "cover"},
                            {"label": f"Binary Sensor ({len(current_binary_sensors)} configured)", "value": "binary_sensor"},
                            {"label": f"Sensor ({len(current_sensors)} configured)", "value": "sensor"},
                            {"label": f"Climate ({len(current_climates)} configured)", "value": "climate"},
                            {"label": f"Media Player ({len(current_media_players)} configured)", "value": "media_player"},
                            {"label": "← Back", "value": "back"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="select_entity_type",
            data_schema=menu_schema,
        )

    async def async_step_join_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Join sync management submenu."""
        if user_input is not None:
            next_step = user_input.get("action")
            if next_step == "add_to_join":
                self.flow._editing_join = None  # Clear editing state
                return await self.flow.async_step_add_to_join()
            elif next_step == "add_from_join":
                self.flow._editing_join = None  # Clear editing state
                return await self.flow.async_step_add_from_join()
            elif next_step == "edit_joins":
                return await self.flow.async_step_select_join_to_edit()
            elif next_step == "remove_joins":
                return await self.flow.async_step_remove_joins()
            elif next_step == "back":
                return await self.flow.async_step_init()

        # Get current join counts
        current_to_joins = self.flow.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.flow.config_entry.data.get(CONF_FROM_HUB, [])
        total_joins = len(current_to_joins) + len(current_from_joins)

        # Show join menu
        menu_schema = vol.Schema(
            {
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": f"Add to_join (HA→Crestron) ({len(current_to_joins)} configured)", "value": "add_to_join"},
                            {"label": f"Add from_join (Crestron→HA) ({len(current_from_joins)} configured)", "value": "add_from_join"},
                            {"label": f"Edit Join ({total_joins} available)", "value": "edit_joins"},
                            {"label": f"Remove Join ({total_joins} available)", "value": "remove_joins"},
                            {"label": "← Back to Main Menu", "value": "back"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="join_menu",
            data_schema=menu_schema,
        )

    async def async_step_dimmer_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dimmer/Keypad management submenu."""
        _LOGGER.debug("async_step_dimmer_menu called with user_input: %s", user_input)
        if user_input is not None:
            next_step = user_input.get("action")
            _LOGGER.debug("Dimmer menu action selected: %s", next_step)
            if next_step == "add_dimmer":
                self.flow._editing_join = None  # Clear editing state
                _LOGGER.debug("Calling async_step_add_dimmer_mode (v1.17.1)")
                return await self.flow.async_step_add_dimmer_mode()
            elif next_step == "edit_dimmers":
                return await self.flow.async_step_select_dimmer_to_edit()
            elif next_step == "remove_dimmers":
                return await self.flow.async_step_remove_dimmers()
            elif next_step == "back":
                return await self.flow.async_step_init()

        # Get current dimmer counts
        current_dimmers = self.flow.config_entry.data.get(CONF_DIMMERS, [])
        total_dimmers = len(current_dimmers)

        # Show dimmer menu
        menu_schema = vol.Schema(
            {
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Add Dimmer/Keypad", "value": "add_dimmer"},
                            {"label": f"Edit Dimmer/Keypad ({total_dimmers} available)", "value": "edit_dimmers"},
                            {"label": f"Remove Dimmer/Keypad ({total_dimmers} available)", "value": "remove_dimmers"},
                            {"label": "← Back to Main Menu", "value": "back"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="dimmer_menu",
            data_schema=menu_schema,
        )
