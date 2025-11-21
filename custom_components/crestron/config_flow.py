"""Config flow for Crestron XSIG integration."""
import logging
import socket
from typing import Any

import voluptuous as vol
import yaml

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector, entity_registry as er, device_registry as dr

from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_TO_HUB,
    CONF_FROM_HUB,
    CONF_COVERS,
    CONF_BINARY_SENSORS,
    CONF_SENSORS,
    CONF_LIGHTS,
    CONF_SWITCHES,
    CONF_CLIMATES,
    CONF_DIMMERS,
    CONF_MEDIA_PLAYERS,
    CONF_POS_JOIN,
    CONF_IS_OPENING_JOIN,
    CONF_IS_CLOSING_JOIN,
    CONF_IS_CLOSED_JOIN,
    CONF_STOP_JOIN,
    CONF_IS_ON_JOIN,
    CONF_VALUE_JOIN,
    CONF_DIVISOR,
    CONF_BRIGHTNESS_JOIN,
    CONF_SWITCH_JOIN,
    # Climate joins - floor_warming
    CONF_FLOOR_MODE_JOIN,
    CONF_FLOOR_MODE_FB_JOIN,
    CONF_FLOOR_SP_JOIN,
    CONF_FLOOR_SP_FB_JOIN,
    CONF_FLOOR_TEMP_JOIN,
    # Climate joins - standard HVAC
    CONF_HEAT_SP_JOIN,
    CONF_COOL_SP_JOIN,
    CONF_REG_TEMP_JOIN,
    CONF_MODE_HEAT_JOIN,
    CONF_MODE_COOL_JOIN,
    CONF_MODE_AUTO_JOIN,
    CONF_MODE_OFF_JOIN,
    CONF_FAN_ON_JOIN,
    CONF_FAN_AUTO_JOIN,
    CONF_H1_JOIN,
    CONF_H2_JOIN,
    CONF_C1_JOIN,
    CONF_C2_JOIN,
    CONF_FA_JOIN,
    CONF_MODE_HEAT_COOL_JOIN,
    CONF_FAN_MODE_AUTO_JOIN,
    CONF_FAN_MODE_ON_JOIN,
    CONF_HVAC_ACTION_HEAT_JOIN,
    CONF_HVAC_ACTION_COOL_JOIN,
    CONF_HVAC_ACTION_IDLE_JOIN,
    # Media player constants (v1.19.0+)
    CONF_MUTE_JOIN,
    CONF_VOLUME_JOIN,
    CONF_SOURCE_NUM_JOIN,
    CONF_SOURCES,
    CONF_POWER_ON_JOIN,
    CONF_POWER_OFF_JOIN,
    CONF_PLAY_JOIN,
    CONF_PAUSE_JOIN,
    CONF_STOP_JOIN,
    CONF_NEXT_JOIN,
    CONF_PREVIOUS_JOIN,
    CONF_REPEAT_JOIN,
    CONF_SHUFFLE_JOIN,
    # Dimmer/Keypad constants (v1.16.x - deprecated)
    CONF_LIGHTING_LOAD,
    CONF_BUTTON_COUNT,
    CONF_BUTTONS,
    CONF_PRESS,
    CONF_DOUBLE_PRESS,
    CONF_HOLD,
    CONF_FEEDBACK,
    CONF_ACTION,
    CONF_SERVICE_DATA,
    DOMAIN_ACTIONS,
    # Dimmer/Keypad constants (v1.17.0+)
    CONF_BASE_JOIN,
    CONF_HAS_LIGHTING_LOAD,
    CONF_LIGHT_ON_JOIN,
    CONF_LIGHT_BRIGHTNESS_JOIN,
)
from homeassistant.const import CONF_NAME, CONF_TYPE, CONF_DEVICE_CLASS, CONF_UNIT_OF_MEASUREMENT

from .config_flow.validators import validate_port, PortInUse, InvalidPort, STEP_USER_DATA_SCHEMA
from .config_flow.base import BaseOptionsFlow

_LOGGER = logging.getLogger(__name__)


class CrestronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Crestron XSIG."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step (user-triggered setup)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate the port
                info = await validate_port(self.hass, user_input[CONF_PORT])

                # Check if we already have a config entry for this port
                await self.async_set_unique_id(f"crestron_{user_input[CONF_PORT]}")
                self._abort_if_unique_id_configured()

                # Create the config entry
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

            except PortInUse:
                errors["port"] = "port_in_use"
            except InvalidPort:
                errors["port"] = "invalid_port"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config flow: %s", err)
                errors["base"] = "unknown"

        # Show the form (initial or with errors)
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Import YAML configuration.

        This flow is triggered automatically when YAML configuration is detected
        on startup and no matching config entry exists.

        Args:
            import_data: Dict from YAML config (contains port, to_joins, from_joins)

        Returns:
            FlowResult creating entry or aborting if already configured
        """
        _LOGGER.info(
            "Importing Crestron YAML configuration on port %s",
            import_data.get(CONF_PORT)
        )

        port = import_data[CONF_PORT]

        # Validate port (but allow if YAML is using it - that's the import case!)
        try:
            info = await validate_port(self.hass, port)
        except (PortInUse, InvalidPort) as err:
            _LOGGER.warning("YAML import validation note: %s", err)
            # For import, create entry anyway - YAML is using the port
            # The existing conflict detection in async_setup_entry will handle it
            info = {"title": f"Crestron XSIG (Port {port}) - Imported from YAML"}

        # Check if already imported (prevent duplicates on restart)
        await self.async_set_unique_id(f"crestron_{port}")
        self._abort_if_unique_id_configured()

        # Store FULL config including to_joins and from_joins
        # This preserves all hub-level configuration
        entry_data = {CONF_PORT: port}

        # Preserve to_joins if exists
        if CONF_TO_HUB in import_data:
            entry_data[CONF_TO_HUB] = import_data[CONF_TO_HUB]
            _LOGGER.info(
                "Imported %d to_joins for bidirectional communication",
                len(import_data[CONF_TO_HUB])
            )

        # Preserve from_joins if exists
        if CONF_FROM_HUB in import_data:
            entry_data[CONF_FROM_HUB] = import_data[CONF_FROM_HUB]
            _LOGGER.info(
                "Imported %d from_joins for Crestron→HA scripts",
                len(import_data[CONF_FROM_HUB])
            )

        _LOGGER.info("YAML import complete - creating config entry with full configuration")

        # Create entry with full hub configuration
        return self.async_create_entry(
            title=info["title"],
            data=entry_data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(BaseOptionsFlow):
    """Handle options flow for Crestron XSIG integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)
        self._editing_join = None  # Track which join we're editing

        # Import handlers here to avoid circular imports
        from .config_flow import MenuHandler, JoinSyncHandler, DimmerHandler
        self._menu_handler = MenuHandler(self)
        self._join_handler = JoinSyncHandler(self)
        self._dimmer_handler = DimmerHandler(self)

        # Import entity handlers here to avoid circular imports
        from .config_flow.entities import (
            EntityManager,
            BinarySensorEntityHandler,
            ClimateEntityHandler,
            CoverEntityHandler,
            LightEntityHandler,
            MediaPlayerEntityHandler,
            SensorEntityHandler,
            SwitchEntityHandler,
        )
        self._entity_manager = EntityManager(self)
        self._binary_sensor_handler = BinarySensorEntityHandler(self)
        self._climate_handler = ClimateEntityHandler(self)
        self._cover_handler = CoverEntityHandler(self)
        self._light_handler = LightEntityHandler(self)
        self._media_player_handler = MediaPlayerEntityHandler(self)
        self._sensor_handler = SensorEntityHandler(self)
        self._switch_handler = SwitchEntityHandler(self)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Main menu - choose between entity, join sync, or dimmer/keypad management."""
        return await self._menu_handler.async_step_init(user_input)

    async def async_step_entity_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Entity management menu."""
        return await self._menu_handler.async_step_entity_menu(user_input)

    async def async_step_select_entity_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select entity type to add."""
        return await self._menu_handler.async_step_select_entity_type(user_input)

    async def async_step_join_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Join sync management menu."""
        return await self._menu_handler.async_step_join_menu(user_input)

    async def async_step_dimmer_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dimmer/keypad management menu."""
        return await self._menu_handler.async_step_dimmer_menu(user_input)

    async def async_step_add_dimmer_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select dimmer join assignment mode."""
        return await self._dimmer_handler.async_step_add_dimmer_mode(user_input)

    async def async_step_add_dimmer_simple(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add dimmer with auto-sequential join assignment."""
        return await self._dimmer_handler.async_step_add_dimmer_simple(user_input)

    async def async_step_add_dimmer_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add dimmer with manual join assignment."""
        return await self._dimmer_handler.async_step_add_dimmer_manual(user_input)

    async def async_step_add_to_join(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add to_join sync rule."""
        return await self._join_handler.async_step_add_to_join(user_input)

    async def async_step_add_from_join(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add from_join sync rule."""
        return await self._join_handler.async_step_add_from_join(user_input)

    async def async_step_remove_joins(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove join sync rules."""
        return await self._join_handler.async_step_remove_joins(user_input)

    async def async_step_select_join_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which join sync rule to edit."""
        return await self._join_handler.async_step_select_join_to_edit(user_input)

    # ========== Entity Configuration Methods (Delegated) ==========

    async def async_step_add_cover(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a cover entity."""
        return await self._cover_handler.async_step_add_cover(user_input)

    async def async_step_add_binary_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a binary sensor entity."""
        return await self._binary_sensor_handler.async_step_add_binary_sensor(user_input)

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a sensor entity."""
        return await self._sensor_handler.async_step_add_sensor(user_input)

    async def async_step_add_light(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a light entity."""
        return await self._light_handler.async_step_add_light(user_input)

    async def async_step_add_switch(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a switch entity."""
        return await self._switch_handler.async_step_add_switch(user_input)

    async def async_step_add_media_player(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a media player entity."""
        return await self._media_player_handler.async_step_add_media_player(user_input)

    async def async_step_add_climate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a climate entity (floor warming)."""
        return await self._climate_handler.async_step_add_climate(user_input)

    async def async_step_select_climate_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select climate type (floor_warming or standard)."""
        return await self._climate_handler.async_step_select_climate_type(user_input)

    async def async_step_add_climate_standard(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a climate entity (standard HVAC)."""
        return await self._climate_handler.async_step_add_climate_standard(user_input)

    async def async_step_select_entity_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which entity to edit."""
        return await self._entity_manager.async_step_select_entity_to_edit(user_input)

    async def async_step_remove_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove entities by selecting from a list."""
        return await self._entity_manager.async_step_remove_entities(user_input)

    # ========== Dimmer/Keypad Configuration Methods ==========

    # ========== Dimmer/Keypad Configuration Methods ==========

    async def async_step_add_dimmer_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Basic dimmer information."""
        return await self._dimmer_handler.async_step_add_dimmer_basic(user_input)

    async def async_step_add_dimmer_lighting(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Configure lighting load (optional)."""
        return await self._dimmer_handler.async_step_add_dimmer_lighting(user_input)

    async def async_step_add_dimmer_button(
        self, user_input: dict[str, Any] | None = None, button_num: int = 1
    ) -> FlowResult:
        """Configure a single button (dynamic, handles buttons 1-6)."""
        return await self._dimmer_handler.async_step_add_dimmer_button(user_input, button_num)

    async def async_step_select_dimmer_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which dimmer to edit."""
        return await self._dimmer_handler.async_step_select_dimmer_to_edit(user_input)

    async def async_step_edit_dimmer(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit an existing dimmer (full reconfiguration)."""
        return await self._dimmer_handler.async_step_edit_dimmer(user_input)

    async def async_step_remove_dimmers(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove selected dimmers."""
        return await self._dimmer_handler.async_step_remove_dimmers(user_input)

