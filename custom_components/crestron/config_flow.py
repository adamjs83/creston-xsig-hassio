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

_LOGGER = logging.getLogger(__name__)

# Port validation schema
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PORT, default=16384): vol.All(
            vol.Coerce(int), vol.Range(min=1024, max=65535)
        ),
    }
)


async def validate_port(hass: HomeAssistant, port: int) -> dict[str, Any]:
    """Validate the port is available and not in use.

    Args:
        hass: Home Assistant instance
        port: Port number to validate

    Returns:
        Dict with validation result

    Raises:
        PortInUse: If port is already in use by external service
        InvalidPort: If port is invalid
    """
    # Check if port is in valid range
    if not 1024 <= port <= 65535:
        raise InvalidPort(f"Port {port} is outside valid range (1024-65535)")

    # Check if YAML configuration is using this port
    # If so, allow it - async_setup_entry will handle the dual-config scenario
    yaml_using_port = False
    if DOMAIN in hass.data and "hub" in hass.data[DOMAIN]:
        yaml_hub = hass.data[DOMAIN]["hub"]
        if hasattr(yaml_hub, 'port') and yaml_hub.port == port:
            yaml_using_port = True
            _LOGGER.info(
                f"Port {port} is in use by YAML configuration. "
                "Config entry will be created but YAML will take precedence."
            )

    # Only check port availability if NOT used by our YAML config
    if not yaml_using_port:
        # Check if port is already in use by testing if we can bind to it
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", port))
        except OSError as err:
            _LOGGER.error(f"Port {port} is already in use by external service: {err}")
            raise PortInUse(f"Port {port} is already in use") from err

    return {"title": f"Crestron XSIG (Port {port})"}


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


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Crestron XSIG integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        # Note: config_entry is available via self.config_entry property from base class
        # Don't set it explicitly to avoid deprecation warning (HA 2025.12+)
        self._editing_join = None  # Track which join we're editing

    async def _async_reload_integration(self) -> None:
        """Safely reload the integration, handling platforms that aren't loaded."""
        try:
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        except ValueError:
            # Some platforms were never loaded, do a full setup cycle
            _LOGGER.debug("Some platforms not loaded, performing unload/setup cycle")
            try:
                await self.hass.config_entries.async_unload(self.config_entry.entry_id)
            except ValueError:
                pass  # Ignore if nothing was loaded
            await self.hass.config_entries.async_setup(self.config_entry.entry_id)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Main menu - choose between entity, join sync, or dimmer/keypad management."""
        if user_input is not None:
            next_step = user_input.get("action")
            if next_step == "entity_menu":
                return await self.async_step_entity_menu()
            elif next_step == "join_menu":
                return await self.async_step_join_menu()
            elif next_step == "dimmer_menu":
                return await self.async_step_dimmer_menu()
            else:
                # Done
                return self.async_create_entry(title="", data={})

        # Get current counts for display
        current_covers = self.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
        current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
        current_climates = self.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.config_entry.data.get(CONF_MEDIA_PLAYERS, [])
        total_entities = len(current_covers) + len(current_binary_sensors) + len(current_sensors) + len(current_lights) + len(current_switches) + len(current_climates) + len(current_media_players)

        current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])
        total_joins = len(current_to_joins) + len(current_from_joins)

        current_dimmers = self.config_entry.data.get(CONF_DIMMERS, [])
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

        return self.async_show_form(
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
                return await self.async_step_select_entity_type()
            elif next_step == "edit_entities":
                return await self.async_step_select_entity_to_edit()
            elif next_step == "remove_entities":
                return await self.async_step_remove_entities()
            elif next_step == "back":
                return await self.async_step_init()

        # Get current entity counts
        current_covers = self.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
        current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
        current_climates = self.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.config_entry.data.get(CONF_MEDIA_PLAYERS, [])
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

        return self.async_show_form(
            step_id="entity_menu",
            data_schema=menu_schema,
        )

    async def async_step_select_entity_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which type of entity to add."""
        if user_input is not None:
            self._editing_join = None  # Clear editing state
            entity_type = user_input.get("entity_type")
            if entity_type == "light":
                return await self.async_step_add_light()
            elif entity_type == "switch":
                return await self.async_step_add_switch()
            elif entity_type == "cover":
                return await self.async_step_add_cover()
            elif entity_type == "binary_sensor":
                return await self.async_step_add_binary_sensor()
            elif entity_type == "sensor":
                return await self.async_step_add_sensor()
            elif entity_type == "climate":
                return await self.async_step_select_climate_type()
            elif entity_type == "media_player":
                return await self.async_step_add_media_player()
            elif entity_type == "back":
                return await self.async_step_entity_menu()

        # Get current counts
        current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
        current_covers = self.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
        current_climates = self.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

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

        return self.async_show_form(
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
                self._editing_join = None  # Clear editing state
                return await self.async_step_add_to_join()
            elif next_step == "add_from_join":
                self._editing_join = None  # Clear editing state
                return await self.async_step_add_from_join()
            elif next_step == "edit_joins":
                return await self.async_step_select_join_to_edit()
            elif next_step == "remove_joins":
                return await self.async_step_remove_joins()
            elif next_step == "back":
                return await self.async_step_init()

        # Get current join counts
        current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])
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

        return self.async_show_form(
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
                self._editing_join = None  # Clear editing state
                _LOGGER.debug("Calling async_step_add_dimmer_mode (v1.17.1)")
                return await self.async_step_add_dimmer_mode()
            elif next_step == "edit_dimmers":
                return await self.async_step_select_dimmer_to_edit()
            elif next_step == "remove_dimmers":
                return await self.async_step_remove_dimmers()
            elif next_step == "back":
                return await self.async_step_init()

        # Get current dimmer counts
        current_dimmers = self.config_entry.data.get(CONF_DIMMERS, [])
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

        return self.async_show_form(
            step_id="dimmer_menu",
            data_schema=menu_schema,
        )

    async def async_step_add_dimmer_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select dimmer join assignment mode (auto-sequential vs manual)."""
        if user_input is not None:
            mode = user_input.get("join_mode")
            if mode == "auto":
                return await self.async_step_add_dimmer_simple()
            else:  # manual
                return await self.async_step_add_dimmer_manual()

        # Show mode selection
        mode_schema = vol.Schema(
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

        return self.async_show_form(
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
                name = user_input.get(CONF_NAME, "").strip()
                base_join_str = user_input.get(CONF_BASE_JOIN, "").strip()
                button_count = int(user_input.get(CONF_BUTTON_COUNT, "4"))
                has_lighting = user_input.get(CONF_HAS_LIGHTING_LOAD, False)
                light_brightness_join_str = user_input.get(CONF_LIGHT_BRIGHTNESS_JOIN, "").strip() if has_lighting else None

                # Validate name
                if not name:
                    errors[CONF_NAME] = "name_required"

                # Validate base join (digital format)
                if not base_join_str or not (base_join_str[0] == 'd' and base_join_str[1:].isdigit()):
                    errors[CONF_BASE_JOIN] = "invalid_join_format"
                else:
                    base_join_num = int(base_join_str[1:])
                    # Validate join range: need button_count * 3 sequential joins
                    max_join_needed = base_join_num + (button_count * 3) - 1
                    if max_join_needed > 250:
                        errors[CONF_BASE_JOIN] = "join_range_exceeded"

                # Validate lighting load brightness join if provided
                if has_lighting:
                    if not light_brightness_join_str or not (light_brightness_join_str[0] == 'a' and light_brightness_join_str[1:].isdigit()):
                        errors[CONF_LIGHT_BRIGHTNESS_JOIN] = "invalid_join_format"

                # Check for join conflicts
                if not errors:
                    joins_to_check = []

                    # Add button joins (press, double, hold for each button)
                    for i in range(button_count):
                        offset = i * 3
                        joins_to_check.append(f"d{base_join_num + offset}")  # press
                        joins_to_check.append(f"d{base_join_num + offset + 1}")  # double
                        joins_to_check.append(f"d{base_join_num + offset + 2}")  # hold

                    # Add lighting load brightness join
                    if has_lighting and light_brightness_join_str:
                        joins_to_check.append(light_brightness_join_str)

                    conflict = self._check_join_conflicts(joins_to_check)
                    if conflict:
                        errors["base"] = "join_conflict"

                if not errors:
                    # Build dimmer config
                    dimmer_config = {
                        CONF_NAME: name,
                        CONF_BASE_JOIN: base_join_str,
                        CONF_BUTTON_COUNT: button_count,
                    }

                    if has_lighting and light_brightness_join_str:
                        dimmer_config[CONF_HAS_LIGHTING_LOAD] = True
                        dimmer_config[CONF_LIGHT_BRIGHTNESS_JOIN] = light_brightness_join_str

                    # Save dimmer
                    current_dimmers = self.config_entry.data.get(CONF_DIMMERS, []).copy()
                    current_dimmers.append(dimmer_config)

                    updated_data = {**self.config_entry.data, CONF_DIMMERS: current_dimmers}
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=updated_data
                    )

                    _LOGGER.info(
                        "Added dimmer '%s' with %d buttons (base join: %s)",
                        name, button_count, base_join_str
                    )

                    # Reload integration
                    await self._async_reload_integration()

                    # Return to dimmer menu
                    return await self.async_step_dimmer_menu()

            except Exception as ex:
                _LOGGER.exception("Unexpected error adding dimmer: %s", ex)
                errors["base"] = "unknown"

        # Show form
        dimmer_schema = vol.Schema(
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

        return self.async_show_form(
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
        if user_input and "button_count" in user_input and not hasattr(self, "_dimmer_button_count"):
            self._dimmer_button_count = int(user_input.get("button_count", "4"))

        if user_input is not None and hasattr(self, "_dimmer_button_count"):
            try:
                name = user_input.get(CONF_NAME, "").strip()
                button_count = self._dimmer_button_count
                has_lighting = user_input.get(CONF_HAS_LIGHTING_LOAD, False)
                light_brightness_join_str = user_input.get(CONF_LIGHT_BRIGHTNESS_JOIN, "").strip() if has_lighting else None

                # Validate name
                if not name:
                    errors[CONF_NAME] = "name_required"

                # Collect and validate button joins
                button_joins = {}
                joins_to_check = []

                for btn_num in range(1, button_count + 1):
                    press_join = user_input.get(f"button_{btn_num}_press", "").strip()
                    double_join = user_input.get(f"button_{btn_num}_double", "").strip()
                    hold_join = user_input.get(f"button_{btn_num}_hold", "").strip()

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
                    conflict = self._check_join_conflicts(joins_to_check)
                    if conflict:
                        errors["base"] = "join_conflict"

                if not errors:
                    # Build dimmer config
                    dimmer_config = {
                        CONF_NAME: name,
                        CONF_BUTTON_COUNT: button_count,
                        "manual_joins": button_joins,  # Store manual join mapping
                    }

                    if has_lighting and light_brightness_join_str:
                        dimmer_config[CONF_HAS_LIGHTING_LOAD] = True
                        dimmer_config[CONF_LIGHT_BRIGHTNESS_JOIN] = light_brightness_join_str

                    # Save dimmer
                    current_dimmers = self.config_entry.data.get(CONF_DIMMERS, []).copy()
                    current_dimmers.append(dimmer_config)

                    updated_data = {**self.config_entry.data, CONF_DIMMERS: current_dimmers}
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=updated_data
                    )

                    _LOGGER.info(
                        "Added dimmer '%s' with %d buttons (manual joins)",
                        name, button_count
                    )

                    # Clear temp state
                    delattr(self, "_dimmer_button_count")

                    # Reload integration
                    await self._async_reload_integration()

                    # Return to dimmer menu
                    return await self.async_step_dimmer_menu()

            except Exception as ex:
                _LOGGER.exception("Unexpected error adding dimmer (manual): %s", ex)
                errors["base"] = "unknown"

        # Build dynamic form based on button count
        button_count = getattr(self, "_dimmer_button_count", int(user_input.get(CONF_BUTTON_COUNT, "4")) if user_input else 4)

        # Build schema fields
        schema_fields = {
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

        dimmer_schema = vol.Schema(schema_fields)

        return self.async_show_form(
            step_id="add_dimmer_manual",
            data_schema=dimmer_schema,
            errors=errors,
        )

    async def async_step_add_to_join(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a single to_join with entity picker."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

        if user_input is not None:
            try:
                join_num = user_input.get("join")
                entity_id = user_input.get("entity_id")
                attribute = user_input.get("attribute", "").strip()
                value_template = user_input.get("value_template", "").strip()

                # Validate join format
                if not join_num or not (join_num[0] in ['d', 'a', 's'] and join_num[1:].isdigit()):
                    errors["join"] = "invalid_join_format"

                # Check for duplicate join (exclude current join if editing)
                current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
                old_join_num = self._editing_join.get("join") if is_editing else None
                if join_num != old_join_num and any(j.get("join") == join_num for j in current_to_joins):
                    errors["join"] = "join_already_exists"

                if not errors:
                    # Build new join entry
                    new_join = {"join": join_num}

                    if entity_id:
                        new_join["entity_id"] = entity_id
                    if attribute:
                        new_join["attribute"] = attribute
                    if value_template:
                        new_join["value_template"] = value_template

                    if is_editing:
                        # Replace existing join
                        updated_to_joins = [
                            new_join if j.get("join") == old_join_num else j
                            for j in current_to_joins
                        ]
                        _LOGGER.info("Updated to_join %s for %s", join_num, entity_id)
                    else:
                        # Append new join
                        updated_to_joins = current_to_joins + [new_join]
                        _LOGGER.info("Added to_join %s for %s", join_num, entity_id)

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_TO_HUB] = updated_to_joins

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/editing to_join: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                "join": self._editing_join.get("join", ""),
                "entity_id": self._editing_join.get("entity_id", ""),
                "attribute": self._editing_join.get("attribute", ""),
                "value_template": self._editing_join.get("value_template", ""),
            }

        # Show form
        add_to_join_schema = vol.Schema(
            {
                vol.Required("join", default=default_values.get("join", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional("entity_id", default=default_values.get("entity_id", "")): selector.EntitySelector(),
                vol.Optional("attribute", default=default_values.get("attribute", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional("value_template", default=default_values.get("value_template", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="add_to_join",
            data_schema=add_to_join_schema,
            errors=errors,
        )

    async def async_step_add_from_join(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a single from_join."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

        if user_input is not None:
            try:
                join_num = user_input.get("join")
                service = user_input.get("service")
                target_entity = user_input.get("target_entity")

                # Validate join format
                if not join_num or not (join_num[0] in ['d', 'a', 's'] and join_num[1:].isdigit()):
                    errors["join"] = "invalid_join_format"

                # Check for duplicate join (exclude current join if editing)
                current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])
                old_join_num = self._editing_join.get("join") if is_editing else None
                if join_num != old_join_num and any(j.get("join") == join_num for j in current_from_joins):
                    errors["join"] = "join_already_exists"

                if not errors:
                    # Build script action
                    script_action = {
                        "service": service,
                    }
                    if target_entity:
                        script_action["target"] = {"entity_id": target_entity}

                    # Build new join entry
                    new_join = {
                        "join": join_num,
                        "script": [script_action]
                    }

                    if is_editing:
                        # Replace existing join
                        updated_from_joins = [
                            new_join if j.get("join") == old_join_num else j
                            for j in current_from_joins
                        ]
                        _LOGGER.info("Updated from_join %s with service %s", join_num, service)
                    else:
                        # Append new join
                        updated_from_joins = current_from_joins + [new_join]
                        _LOGGER.info("Added from_join %s with service %s", join_num, service)

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_FROM_HUB] = updated_from_joins

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/editing from_join: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            script_action = self._editing_join.get("script", [{}])[0] if self._editing_join.get("script") else {}
            default_values = {
                "join": self._editing_join.get("join", ""),
                "service": script_action.get("service", ""),
                "target_entity": script_action.get("target", {}).get("entity_id", ""),
            }

        # Show form
        add_from_join_schema = vol.Schema(
            {
                vol.Required("join", default=default_values.get("join", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required("service", default=default_values.get("service", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional("target_entity", default=default_values.get("target_entity", "")): selector.EntitySelector(),
            }
        )

        return self.async_show_form(
            step_id="add_from_join",
            data_schema=add_from_join_schema,
            errors=errors,
        )

    async def async_step_remove_joins(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove joins by selecting from a list."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                joins_to_remove = user_input.get("joins_to_remove", [])

                if joins_to_remove:
                    current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
                    current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])

                    # Filter out selected joins
                    updated_to_joins = [j for j in current_to_joins if j.get("join") not in joins_to_remove]
                    updated_from_joins = [j for j in current_from_joins if j.get("join") not in joins_to_remove]

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_TO_HUB] = updated_to_joins
                    new_data[CONF_FROM_HUB] = updated_from_joins

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    _LOGGER.info("Removed %d joins", len(joins_to_remove))

                # Return to menu
                return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error removing joins: %s", err)
                errors["base"] = "unknown"

        # Build list of all joins for removal selection
        current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])

        join_options = []
        for j in current_to_joins:
            entity = j.get("entity_id", j.get("value_template", "N/A"))
            join_options.append({
                "label": f"{j.get('join')} → {entity} (to_join)",
                "value": j.get("join")
            })

        for j in current_from_joins:
            script_info = "script" if "script" in j else "N/A"
            join_options.append({
                "label": f"{j.get('join')} → {script_info} (from_join)",
                "value": j.get("join")
            })

        if not join_options:
            # No joins to remove, return to menu
            return await self.async_step_init()

        # Show removal form
        remove_schema = vol.Schema(
            {
                vol.Optional("joins_to_remove"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=join_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="remove_joins",
            data_schema=remove_schema,
            errors=errors,
        )

    async def async_step_select_join_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which join to edit."""
        if user_input is not None:
            selected_join = user_input.get("join_to_edit")

            if selected_join:
                # Find the join in our data
                current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
                current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])

                # Check if it's a to_join or from_join
                for join in current_to_joins:
                    if join.get("join") == selected_join:
                        self._editing_join = join
                        return await self.async_step_add_to_join()

                for join in current_from_joins:
                    if join.get("join") == selected_join:
                        self._editing_join = join
                        return await self.async_step_add_from_join()

            # If no join selected, return to menu
            return await self.async_step_init()

        # Build list of all joins for editing
        current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])

        join_options = []
        for j in current_to_joins:
            entity = j.get("entity_id", j.get("value_template", "N/A"))
            join_options.append({
                "label": f"{j.get('join')} → {entity} (to_join)",
                "value": j.get("join")
            })

        for j in current_from_joins:
            script_info = "script" if "script" in j else "N/A"
            join_options.append({
                "label": f"{j.get('join')} → {script_info} (from_join)",
                "value": j.get("join")
            })

        if not join_options:
            # No joins to edit, return to menu
            return await self.async_step_init()

        # Show selection form
        select_schema = vol.Schema(
            {
                vol.Required("join_to_edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=join_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="select_join_to_edit",
            data_schema=select_schema,
        )

    async def async_step_add_cover(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a cover entity."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

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
                current_covers = self.config_entry.data.get(CONF_COVERS, [])
                old_name = self._editing_join.get(CONF_NAME) if is_editing else None
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
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_COVERS] = updated_covers

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating cover: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                CONF_NAME: self._editing_join.get(CONF_NAME, ""),
                CONF_POS_JOIN: self._editing_join.get(CONF_POS_JOIN, ""),
                CONF_TYPE: self._editing_join.get(CONF_TYPE, "shade"),
                CONF_IS_OPENING_JOIN: self._editing_join.get(CONF_IS_OPENING_JOIN, ""),
                CONF_IS_CLOSING_JOIN: self._editing_join.get(CONF_IS_CLOSING_JOIN, ""),
                CONF_IS_CLOSED_JOIN: self._editing_join.get(CONF_IS_CLOSED_JOIN, ""),
                CONF_STOP_JOIN: self._editing_join.get(CONF_STOP_JOIN, ""),
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

        return self.async_show_form(
            step_id="add_cover",
            data_schema=add_cover_schema,
            errors=errors,
        )

    async def async_step_add_binary_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a binary sensor entity."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME)
                is_on_join = user_input.get(CONF_IS_ON_JOIN)
                device_class = user_input.get(CONF_DEVICE_CLASS)

                # Validate is_on_join format (must be digital)
                if not is_on_join or not (is_on_join[0] == 'd' and is_on_join[1:].isdigit()):
                    errors[CONF_IS_ON_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
                old_name = self._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(bs.get(CONF_NAME) == name for bs in current_binary_sensors):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new binary sensor entry
                    new_binary_sensor = {
                        CONF_NAME: name,
                        CONF_IS_ON_JOIN: is_on_join,
                        CONF_DEVICE_CLASS: device_class,
                    }

                    if is_editing:
                        # Replace existing binary sensor
                        updated_binary_sensors = [
                            new_binary_sensor if bs.get(CONF_NAME) == old_name else bs
                            for bs in current_binary_sensors
                        ]
                        _LOGGER.info("Updated binary sensor %s", name)
                    else:
                        # Append new binary sensor
                        updated_binary_sensors = current_binary_sensors + [new_binary_sensor]
                        _LOGGER.info("Added binary sensor %s", name)

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_BINARY_SENSORS] = updated_binary_sensors

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating binary sensor: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                CONF_NAME: self._editing_join.get(CONF_NAME, ""),
                CONF_IS_ON_JOIN: self._editing_join.get(CONF_IS_ON_JOIN, ""),
                CONF_DEVICE_CLASS: self._editing_join.get(CONF_DEVICE_CLASS, "motion"),
            }

        # Show form
        add_binary_sensor_schema = vol.Schema(
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
                vol.Required(CONF_DEVICE_CLASS, default=default_values.get(CONF_DEVICE_CLASS, "motion")): selector.SelectSelector(
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

        return self.async_show_form(
            step_id="add_binary_sensor",
            data_schema=add_binary_sensor_schema,
            errors=errors,
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a sensor entity."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME)
                value_join = user_input.get(CONF_VALUE_JOIN)
                device_class = user_input.get(CONF_DEVICE_CLASS)
                unit_of_measurement = user_input.get(CONF_UNIT_OF_MEASUREMENT)
                divisor = user_input.get(CONF_DIVISOR, 1)

                # Validate value_join format (must be analog)
                if not value_join or not (value_join[0] == 'a' and value_join[1:].isdigit()):
                    errors[CONF_VALUE_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
                old_name = self._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(s.get(CONF_NAME) == name for s in current_sensors):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new sensor entry
                    new_sensor = {
                        CONF_NAME: name,
                        CONF_VALUE_JOIN: value_join,
                        CONF_DEVICE_CLASS: device_class,
                        CONF_UNIT_OF_MEASUREMENT: unit_of_measurement,
                        CONF_DIVISOR: divisor,
                    }

                    if is_editing:
                        # Replace existing sensor
                        updated_sensors = [
                            new_sensor if s.get(CONF_NAME) == old_name else s
                            for s in current_sensors
                        ]
                        _LOGGER.info("Updated sensor %s", name)
                    else:
                        # Append new sensor
                        updated_sensors = current_sensors + [new_sensor]
                        _LOGGER.info("Added sensor %s", name)

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_SENSORS] = updated_sensors

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating sensor: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                CONF_NAME: self._editing_join.get(CONF_NAME, ""),
                CONF_VALUE_JOIN: self._editing_join.get(CONF_VALUE_JOIN, ""),
                CONF_DEVICE_CLASS: self._editing_join.get(CONF_DEVICE_CLASS, "temperature"),
                CONF_UNIT_OF_MEASUREMENT: self._editing_join.get(CONF_UNIT_OF_MEASUREMENT, ""),
                CONF_DIVISOR: self._editing_join.get(CONF_DIVISOR, 1),
            }

        # Show form
        add_sensor_schema = vol.Schema(
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

        return self.async_show_form(
            step_id="add_sensor",
            data_schema=add_sensor_schema,
            errors=errors,
        )

    async def async_step_add_light(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a light entity."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME)
                brightness_join = user_input.get(CONF_BRIGHTNESS_JOIN)
                light_type = user_input.get(CONF_TYPE, "brightness")

                # Validate brightness_join format (must be analog)
                if not brightness_join or not (brightness_join[0] == 'a' and brightness_join[1:].isdigit()):
                    errors[CONF_BRIGHTNESS_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
                old_name = self._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(l.get(CONF_NAME) == name for l in current_lights):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new light entry
                    new_light = {
                        CONF_NAME: name,
                        CONF_BRIGHTNESS_JOIN: brightness_join,
                        CONF_TYPE: light_type,
                    }

                    if is_editing:
                        # Replace existing light
                        updated_lights = [
                            new_light if l.get(CONF_NAME) == old_name else l
                            for l in current_lights
                        ]
                        _LOGGER.info("Updated light %s", name)
                    else:
                        # Append new light
                        updated_lights = current_lights + [new_light]
                        _LOGGER.info("Added light %s", name)

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_LIGHTS] = updated_lights

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating light: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                CONF_NAME: self._editing_join.get(CONF_NAME, ""),
                CONF_BRIGHTNESS_JOIN: self._editing_join.get(CONF_BRIGHTNESS_JOIN, ""),
                CONF_TYPE: self._editing_join.get(CONF_TYPE, "brightness"),
            }

        # Show form
        add_light_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_BRIGHTNESS_JOIN, default=default_values.get(CONF_BRIGHTNESS_JOIN, "")): selector.TextSelector(
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

        return self.async_show_form(
            step_id="add_light",
            data_schema=add_light_schema,
            errors=errors,
        )

    async def async_step_add_switch(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a switch entity."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME)
                switch_join = user_input.get(CONF_SWITCH_JOIN)
                device_class = user_input.get(CONF_DEVICE_CLASS, "switch")

                # Validate switch_join format (must be digital)
                if not switch_join or not (switch_join[0] == 'd' and switch_join[1:].isdigit()):
                    errors[CONF_SWITCH_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
                old_name = self._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(s.get(CONF_NAME) == name for s in current_switches):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new switch entry
                    new_switch = {
                        CONF_NAME: name,
                        CONF_SWITCH_JOIN: switch_join,
                        CONF_DEVICE_CLASS: device_class,
                    }

                    if is_editing:
                        # Replace existing switch
                        updated_switches = [
                            new_switch if s.get(CONF_NAME) == old_name else s
                            for s in current_switches
                        ]
                        _LOGGER.info("Updated switch %s", name)
                    else:
                        # Append new switch
                        updated_switches = current_switches + [new_switch]
                        _LOGGER.info("Added switch %s", name)

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_SWITCHES] = updated_switches

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating switch: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                CONF_NAME: self._editing_join.get(CONF_NAME, ""),
                CONF_SWITCH_JOIN: self._editing_join.get(CONF_SWITCH_JOIN, ""),
                CONF_DEVICE_CLASS: self._editing_join.get(CONF_DEVICE_CLASS, "switch"),
            }

        # Show form
        add_switch_schema = vol.Schema(
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

        return self.async_show_form(
            step_id="add_switch",
            data_schema=add_switch_schema,
            errors=errors,
        )

    async def async_step_add_media_player(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a media player entity."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME)
                device_class = user_input.get(CONF_DEVICE_CLASS, "speaker")
                source_num_join = user_input.get(CONF_SOURCE_NUM_JOIN)
                sources_text = user_input.get(CONF_SOURCES, "")

                # Optional joins
                power_on_join = user_input.get(CONF_POWER_ON_JOIN, "")
                mute_join = user_input.get(CONF_MUTE_JOIN, "")
                volume_join = user_input.get(CONF_VOLUME_JOIN, "")
                play_join = user_input.get(CONF_PLAY_JOIN, "")
                pause_join = user_input.get(CONF_PAUSE_JOIN, "")
                stop_join = user_input.get(CONF_STOP_JOIN, "")
                next_join = user_input.get(CONF_NEXT_JOIN, "")
                previous_join = user_input.get(CONF_PREVIOUS_JOIN, "")

                # Validate source_num_join (required, analog)
                if not source_num_join or not (source_num_join[0] == 'a' and source_num_join[1:].isdigit()):
                    errors[CONF_SOURCE_NUM_JOIN] = "invalid_join_format"

                # Parse and validate sources (required, min 1 source)
                sources_dict = {}
                if sources_text.strip():
                    for line in sources_text.strip().split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        if ':' not in line:
                            errors[CONF_SOURCES] = "invalid_source_format"
                            break
                        try:
                            num_str, name_str = line.split(':', 1)
                            source_num = int(num_str.strip())
                            source_name = name_str.strip()
                            if source_num < 1 or source_num > 99:
                                errors[CONF_SOURCES] = "source_number_out_of_range"
                                break
                            sources_dict[source_num] = source_name
                        except (ValueError, AttributeError):
                            errors[CONF_SOURCES] = "invalid_source_format"
                            break

                if not sources_dict:
                    errors[CONF_SOURCES] = "no_sources_configured"

                # Validate optional joins
                optional_joins = [
                    (CONF_POWER_ON_JOIN, power_on_join, 'd'),
                    (CONF_MUTE_JOIN, mute_join, 'd'),
                    (CONF_VOLUME_JOIN, volume_join, 'a'),
                    (CONF_PLAY_JOIN, play_join, 'd'),
                    (CONF_PAUSE_JOIN, pause_join, 'd'),
                    (CONF_STOP_JOIN, stop_join, 'd'),
                    (CONF_NEXT_JOIN, next_join, 'd'),
                    (CONF_PREVIOUS_JOIN, previous_join, 'd'),
                ]

                for join_field, join_value, join_type in optional_joins:
                    if join_value and not (join_value[0] == join_type and join_value[1:].isdigit()):
                        errors[join_field] = "invalid_join_format"

                # Check for duplicate entity name
                current_media_players = self.config_entry.data.get(CONF_MEDIA_PLAYERS, [])
                old_name = self._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(mp.get(CONF_NAME) == name for mp in current_media_players):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new media player entry
                    new_media_player = {
                        CONF_NAME: name,
                        CONF_DEVICE_CLASS: device_class,
                        CONF_SOURCE_NUM_JOIN: source_num_join,
                        CONF_SOURCES: sources_dict,
                    }

                    # Add optional joins if provided
                    if power_on_join:
                        new_media_player[CONF_POWER_ON_JOIN] = power_on_join
                    if mute_join:
                        new_media_player[CONF_MUTE_JOIN] = mute_join
                    if volume_join:
                        new_media_player[CONF_VOLUME_JOIN] = volume_join
                    if play_join:
                        new_media_player[CONF_PLAY_JOIN] = play_join
                    if pause_join:
                        new_media_player[CONF_PAUSE_JOIN] = pause_join
                    if stop_join:
                        new_media_player[CONF_STOP_JOIN] = stop_join
                    if next_join:
                        new_media_player[CONF_NEXT_JOIN] = next_join
                    if previous_join:
                        new_media_player[CONF_PREVIOUS_JOIN] = previous_join

                    if is_editing:
                        # Replace existing media player
                        updated_media_players = [
                            new_media_player if mp.get(CONF_NAME) == old_name else mp
                            for mp in current_media_players
                        ]
                        _LOGGER.info("Updated media player %s", name)
                    else:
                        # Append new media player
                        updated_media_players = current_media_players + [new_media_player]
                        _LOGGER.info("Added media player %s", name)

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_MEDIA_PLAYERS] = updated_media_players

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating media player: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            # Convert sources dict to text format
            sources_dict = self._editing_join.get(CONF_SOURCES, {})
            sources_text = '\n'.join(f"{num}: {name}" for num, name in sorted(sources_dict.items()))

            default_values = {
                CONF_NAME: self._editing_join.get(CONF_NAME, ""),
                CONF_DEVICE_CLASS: self._editing_join.get(CONF_DEVICE_CLASS, "speaker"),
                CONF_SOURCE_NUM_JOIN: self._editing_join.get(CONF_SOURCE_NUM_JOIN, ""),
                CONF_SOURCES: sources_text,
                CONF_POWER_ON_JOIN: self._editing_join.get(CONF_POWER_ON_JOIN, ""),
                CONF_MUTE_JOIN: self._editing_join.get(CONF_MUTE_JOIN, ""),
                CONF_VOLUME_JOIN: self._editing_join.get(CONF_VOLUME_JOIN, ""),
                CONF_PLAY_JOIN: self._editing_join.get(CONF_PLAY_JOIN, ""),
                CONF_PAUSE_JOIN: self._editing_join.get(CONF_PAUSE_JOIN, ""),
                CONF_STOP_JOIN: self._editing_join.get(CONF_STOP_JOIN, ""),
                CONF_NEXT_JOIN: self._editing_join.get(CONF_NEXT_JOIN, ""),
                CONF_PREVIOUS_JOIN: self._editing_join.get(CONF_PREVIOUS_JOIN, ""),
            }

        # Show form
        add_media_player_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_DEVICE_CLASS, default=default_values.get(CONF_DEVICE_CLASS, "speaker")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "TV", "value": "tv"},
                            {"label": "Speaker", "value": "speaker"},
                            {"label": "Receiver", "value": "receiver"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_SOURCE_NUM_JOIN, default=default_values.get(CONF_SOURCE_NUM_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_SOURCES, default=default_values.get(CONF_SOURCES, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                        multiline=True,
                    )
                ),
                vol.Optional(CONF_POWER_ON_JOIN, default=default_values.get(CONF_POWER_ON_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_MUTE_JOIN, default=default_values.get(CONF_MUTE_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_VOLUME_JOIN, default=default_values.get(CONF_VOLUME_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_PLAY_JOIN, default=default_values.get(CONF_PLAY_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_PAUSE_JOIN, default=default_values.get(CONF_PAUSE_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_STOP_JOIN, default=default_values.get(CONF_STOP_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_NEXT_JOIN, default=default_values.get(CONF_NEXT_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_PREVIOUS_JOIN, default=default_values.get(CONF_PREVIOUS_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="add_media_player",
            data_schema=add_media_player_schema,
            errors=errors,
            description_placeholders={
                "sources_help": "Enter one source per line in format: number: name\nExample:\n1: HDMI 1\n2: HDMI 2\n3: Chromecast"
            },
        )

    async def async_step_add_climate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a climate entity (floor warming only)."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME)
                floor_mode_join = user_input.get(CONF_FLOOR_MODE_JOIN)
                floor_mode_fb_join = user_input.get(CONF_FLOOR_MODE_FB_JOIN)
                floor_sp_join = user_input.get(CONF_FLOOR_SP_JOIN)
                floor_sp_fb_join = user_input.get(CONF_FLOOR_SP_FB_JOIN)
                floor_temp_join = user_input.get(CONF_FLOOR_TEMP_JOIN)

                # Validate all joins are analog format
                joins_to_validate = [
                    (CONF_FLOOR_MODE_JOIN, floor_mode_join),
                    (CONF_FLOOR_MODE_FB_JOIN, floor_mode_fb_join),
                    (CONF_FLOOR_SP_JOIN, floor_sp_join),
                    (CONF_FLOOR_SP_FB_JOIN, floor_sp_fb_join),
                    (CONF_FLOOR_TEMP_JOIN, floor_temp_join),
                ]

                for join_field, join_value in joins_to_validate:
                    if not join_value or not (join_value[0] == 'a' and join_value[1:].isdigit()):
                        errors[join_field] = "invalid_join_format"

                # Check for duplicate entity name
                current_climates = self.config_entry.data.get(CONF_CLIMATES, [])
                old_name = self._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(c.get(CONF_NAME) == name for c in current_climates):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new climate entry (floor_warming type only)
                    new_climate = {
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
                        updated_climates = [
                            new_climate if c.get(CONF_NAME) == old_name else c
                            for c in current_climates
                        ]
                        _LOGGER.info("Updated climate %s", name)
                    else:
                        # Append new climate
                        updated_climates = current_climates + [new_climate]
                        _LOGGER.info("Added climate %s", name)

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_CLIMATES] = updated_climates

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating climate: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                CONF_NAME: self._editing_join.get(CONF_NAME, ""),
                CONF_FLOOR_MODE_JOIN: self._editing_join.get(CONF_FLOOR_MODE_JOIN, ""),
                CONF_FLOOR_MODE_FB_JOIN: self._editing_join.get(CONF_FLOOR_MODE_FB_JOIN, ""),
                CONF_FLOOR_SP_JOIN: self._editing_join.get(CONF_FLOOR_SP_JOIN, ""),
                CONF_FLOOR_SP_FB_JOIN: self._editing_join.get(CONF_FLOOR_SP_FB_JOIN, ""),
                CONF_FLOOR_TEMP_JOIN: self._editing_join.get(CONF_FLOOR_TEMP_JOIN, ""),
            }

        # Show form
        add_climate_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_FLOOR_MODE_JOIN, default=default_values.get(CONF_FLOOR_MODE_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_FLOOR_MODE_FB_JOIN, default=default_values.get(CONF_FLOOR_MODE_FB_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_FLOOR_SP_JOIN, default=default_values.get(CONF_FLOOR_SP_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_FLOOR_SP_FB_JOIN, default=default_values.get(CONF_FLOOR_SP_FB_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_FLOOR_TEMP_JOIN, default=default_values.get(CONF_FLOOR_TEMP_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="add_climate",
            data_schema=add_climate_schema,
            errors=errors,
        )

    async def async_step_select_climate_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select climate type (floor_warming or standard)."""
        if user_input is not None:
            climate_type = user_input.get("climate_type")
            if climate_type == "floor_warming":
                return await self.async_step_add_climate()
            elif climate_type == "standard":
                return await self.async_step_add_climate_standard()

        # Show type selection form
        type_schema = vol.Schema(
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

        return self.async_show_form(
            step_id="select_climate_type",
            data_schema=type_schema,
        )

    async def async_step_add_climate_standard(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a standard HVAC climate entity."""
        errors: dict[str, str] = {}
        is_editing = self._editing_join is not None

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME)

                # Validate analog joins (3 required)
                analog_joins = {
                    CONF_HEAT_SP_JOIN: user_input.get(CONF_HEAT_SP_JOIN),
                    CONF_COOL_SP_JOIN: user_input.get(CONF_COOL_SP_JOIN),
                    CONF_REG_TEMP_JOIN: user_input.get(CONF_REG_TEMP_JOIN),
                }

                for join_field, join_value in analog_joins.items():
                    if not join_value or not (join_value[0] == 'a' and join_value[1:].isdigit()):
                        errors[join_field] = "invalid_join_format"

                # Validate digital joins (15 required)
                digital_joins = {
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
                    if not join_value or not (join_value[0] == 'd' and join_value[1:].isdigit()):
                        errors[join_field] = "invalid_join_format"

                # Validate optional digital joins (2 optional)
                h2_join = user_input.get(CONF_H2_JOIN, "")
                c2_join = user_input.get(CONF_C2_JOIN, "")

                if h2_join and not (h2_join[0] == 'd' and h2_join[1:].isdigit()):
                    errors[CONF_H2_JOIN] = "invalid_join_format"
                if c2_join and not (c2_join[0] == 'd' and c2_join[1:].isdigit()):
                    errors[CONF_C2_JOIN] = "invalid_join_format"

                # Check for duplicate entity name
                current_climates = self.config_entry.data.get(CONF_CLIMATES, [])
                old_name = self._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(c.get(CONF_NAME) == name for c in current_climates):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new climate entry (standard type)
                    new_climate = {
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
                        updated_climates = [
                            new_climate if c.get(CONF_NAME) == old_name else c
                            for c in current_climates
                        ]
                        _LOGGER.info("Updated standard climate %s", name)
                    else:
                        # Append new climate
                        updated_climates = current_climates + [new_climate]
                        _LOGGER.info("Added standard climate %s", name)

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_CLIMATES] = updated_climates

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    # Clear editing state and return to menu
                    self._editing_join = None
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating standard climate: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                CONF_NAME: self._editing_join.get(CONF_NAME, ""),
                CONF_HEAT_SP_JOIN: self._editing_join.get(CONF_HEAT_SP_JOIN, ""),
                CONF_COOL_SP_JOIN: self._editing_join.get(CONF_COOL_SP_JOIN, ""),
                CONF_REG_TEMP_JOIN: self._editing_join.get(CONF_REG_TEMP_JOIN, ""),
                CONF_MODE_HEAT_JOIN: self._editing_join.get(CONF_MODE_HEAT_JOIN, ""),
                CONF_MODE_COOL_JOIN: self._editing_join.get(CONF_MODE_COOL_JOIN, ""),
                CONF_MODE_AUTO_JOIN: self._editing_join.get(CONF_MODE_AUTO_JOIN, ""),
                CONF_MODE_OFF_JOIN: self._editing_join.get(CONF_MODE_OFF_JOIN, ""),
                CONF_FAN_ON_JOIN: self._editing_join.get(CONF_FAN_ON_JOIN, ""),
                CONF_FAN_AUTO_JOIN: self._editing_join.get(CONF_FAN_AUTO_JOIN, ""),
                CONF_H1_JOIN: self._editing_join.get(CONF_H1_JOIN, ""),
                CONF_H2_JOIN: self._editing_join.get(CONF_H2_JOIN, ""),
                CONF_C1_JOIN: self._editing_join.get(CONF_C1_JOIN, ""),
                CONF_C2_JOIN: self._editing_join.get(CONF_C2_JOIN, ""),
                CONF_FA_JOIN: self._editing_join.get(CONF_FA_JOIN, ""),
                CONF_MODE_HEAT_COOL_JOIN: self._editing_join.get(CONF_MODE_HEAT_COOL_JOIN, ""),
                CONF_FAN_MODE_AUTO_JOIN: self._editing_join.get(CONF_FAN_MODE_AUTO_JOIN, ""),
                CONF_FAN_MODE_ON_JOIN: self._editing_join.get(CONF_FAN_MODE_ON_JOIN, ""),
                CONF_HVAC_ACTION_HEAT_JOIN: self._editing_join.get(CONF_HVAC_ACTION_HEAT_JOIN, ""),
                CONF_HVAC_ACTION_COOL_JOIN: self._editing_join.get(CONF_HVAC_ACTION_COOL_JOIN, ""),
                CONF_HVAC_ACTION_IDLE_JOIN: self._editing_join.get(CONF_HVAC_ACTION_IDLE_JOIN, ""),
            }

        # Show form - organized by section
        add_climate_standard_schema = vol.Schema(
            {
                # Name
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                # Temperature setpoints (3 analog)
                vol.Required(CONF_HEAT_SP_JOIN, default=default_values.get(CONF_HEAT_SP_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_COOL_SP_JOIN, default=default_values.get(CONF_COOL_SP_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_REG_TEMP_JOIN, default=default_values.get(CONF_REG_TEMP_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                # HVAC modes (5 digital)
                vol.Required(CONF_MODE_HEAT_JOIN, default=default_values.get(CONF_MODE_HEAT_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_MODE_COOL_JOIN, default=default_values.get(CONF_MODE_COOL_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_MODE_AUTO_JOIN, default=default_values.get(CONF_MODE_AUTO_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_MODE_HEAT_COOL_JOIN, default=default_values.get(CONF_MODE_HEAT_COOL_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_MODE_OFF_JOIN, default=default_values.get(CONF_MODE_OFF_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                # Fan modes (4 digital)
                vol.Required(CONF_FAN_ON_JOIN, default=default_values.get(CONF_FAN_ON_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_FAN_AUTO_JOIN, default=default_values.get(CONF_FAN_AUTO_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_FAN_MODE_ON_JOIN, default=default_values.get(CONF_FAN_MODE_ON_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_FAN_MODE_AUTO_JOIN, default=default_values.get(CONF_FAN_MODE_AUTO_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
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
                vol.Required(CONF_HVAC_ACTION_HEAT_JOIN, default=default_values.get(CONF_HVAC_ACTION_HEAT_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_HVAC_ACTION_COOL_JOIN, default=default_values.get(CONF_HVAC_ACTION_COOL_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_HVAC_ACTION_IDLE_JOIN, default=default_values.get(CONF_HVAC_ACTION_IDLE_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
            }
        )

        return self.async_show_form(
            step_id="add_climate_standard",
            data_schema=add_climate_standard_schema,
            errors=errors,
        )

    async def async_step_select_entity_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which entity to edit."""
        if user_input is not None:
            selected_entity = user_input.get("entity_to_edit")

            if selected_entity:
                # Find the entity in our data
                current_covers = self.config_entry.data.get(CONF_COVERS, [])
                current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
                current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
                current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
                current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
                current_climates = self.config_entry.data.get(CONF_CLIMATES, [])
                current_media_players = self.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

                # Check if it's a light
                for light in current_lights:
                    if light.get(CONF_NAME) == selected_entity:
                        self._editing_join = light
                        return await self.async_step_add_light()

                # Check if it's a switch
                for switch in current_switches:
                    if switch.get(CONF_NAME) == selected_entity:
                        self._editing_join = switch
                        return await self.async_step_add_switch()

                # Check if it's a cover
                for cover in current_covers:
                    if cover.get(CONF_NAME) == selected_entity:
                        self._editing_join = cover
                        return await self.async_step_add_cover()

                # Check if it's a binary sensor
                for binary_sensor in current_binary_sensors:
                    if binary_sensor.get(CONF_NAME) == selected_entity:
                        self._editing_join = binary_sensor
                        return await self.async_step_add_binary_sensor()

                # Check if it's a sensor
                for sensor in current_sensors:
                    if sensor.get(CONF_NAME) == selected_entity:
                        self._editing_join = sensor
                        return await self.async_step_add_sensor()

                # Check if it's a climate
                for climate in current_climates:
                    if climate.get(CONF_NAME) == selected_entity:
                        self._editing_join = climate
                        # Route to appropriate climate form based on type
                        climate_type = climate.get(CONF_TYPE, "standard")
                        if climate_type == "floor_warming":
                            return await self.async_step_add_climate()
                        else:
                            return await self.async_step_add_climate_standard()

                # Check if it's a media player
                for media_player in current_media_players:
                    if media_player.get(CONF_NAME) == selected_entity:
                        self._editing_join = media_player
                        return await self.async_step_add_media_player()

            # Not found, return to menu
            return await self.async_step_init()

        # Build list of all entities for editing
        current_covers = self.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
        current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
        current_climates = self.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

        entity_options = []
        for l in current_lights:
            entity_options.append({
                "label": f"{l.get(CONF_NAME)} (Light - {l.get(CONF_BRIGHTNESS_JOIN)})",
                "value": l.get(CONF_NAME)
            })
        for sw in current_switches:
            entity_options.append({
                "label": f"{sw.get(CONF_NAME)} (Switch - {sw.get(CONF_SWITCH_JOIN)})",
                "value": sw.get(CONF_NAME)
            })
        for c in current_covers:
            entity_options.append({
                "label": f"{c.get(CONF_NAME)} (Cover - {c.get(CONF_POS_JOIN)})",
                "value": c.get(CONF_NAME)
            })
        for bs in current_binary_sensors:
            entity_options.append({
                "label": f"{bs.get(CONF_NAME)} (Binary Sensor - {bs.get(CONF_IS_ON_JOIN)})",
                "value": bs.get(CONF_NAME)
            })
        for s in current_sensors:
            entity_options.append({
                "label": f"{s.get(CONF_NAME)} (Sensor - {s.get(CONF_VALUE_JOIN)})",
                "value": s.get(CONF_NAME)
            })
        for cl in current_climates:
            climate_type = cl.get(CONF_TYPE, "standard")
            type_label = "Floor Warming" if climate_type == "floor_warming" else "Standard HVAC"
            join_display = cl.get(CONF_FLOOR_SP_JOIN) if climate_type == "floor_warming" else cl.get(CONF_HEAT_SP_JOIN)
            entity_options.append({
                "label": f"{cl.get(CONF_NAME)} (Climate - {type_label} - {join_display})",
                "value": cl.get(CONF_NAME)
            })
        for mp in current_media_players:
            entity_options.append({
                "label": f"{mp.get(CONF_NAME)} (Media Player - {mp.get(CONF_SOURCE_NUM_JOIN)})",
                "value": mp.get(CONF_NAME)
            })

        if not entity_options:
            # No entities to edit, return to menu
            return await self.async_step_init()

        # Show selection form
        select_schema = vol.Schema(
            {
                vol.Required("entity_to_edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=entity_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="select_entity_to_edit",
            data_schema=select_schema,
        )

    async def async_step_remove_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove entities by selecting from a list."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                entities_to_remove = user_input.get("entities_to_remove", [])

                if entities_to_remove:
                    current_covers = self.config_entry.data.get(CONF_COVERS, [])
                    current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
                    current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
                    current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
                    current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
                    current_climates = self.config_entry.data.get(CONF_CLIMATES, [])
                    current_media_players = self.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

                    # Filter out selected entities
                    updated_covers = [c for c in current_covers if c.get(CONF_NAME) not in entities_to_remove]
                    updated_binary_sensors = [bs for bs in current_binary_sensors if bs.get(CONF_NAME) not in entities_to_remove]
                    updated_sensors = [s for s in current_sensors if s.get(CONF_NAME) not in entities_to_remove]
                    updated_lights = [l for l in current_lights if l.get(CONF_NAME) not in entities_to_remove]
                    updated_switches = [sw for sw in current_switches if sw.get(CONF_NAME) not in entities_to_remove]
                    updated_climates = [cl for cl in current_climates if cl.get(CONF_NAME) not in entities_to_remove]
                    updated_media_players = [mp for mp in current_media_players if mp.get(CONF_NAME) not in entities_to_remove]

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_COVERS] = updated_covers
                    new_data[CONF_BINARY_SENSORS] = updated_binary_sensors
                    new_data[CONF_SENSORS] = updated_sensors
                    new_data[CONF_LIGHTS] = updated_lights
                    new_data[CONF_SWITCHES] = updated_switches
                    new_data[CONF_CLIMATES] = updated_climates
                    new_data[CONF_MEDIA_PLAYERS] = updated_media_players

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Remove entities from entity registry
                    entity_reg = er.async_get(self.hass)
                    removed_count = 0

                    for entity_name in entities_to_remove:
                        # Find the entity config to get join number
                        entity_config = None
                        entity_type = None

                        # Check if it's a light
                        for light in current_lights:
                            if light.get(CONF_NAME) == entity_name:
                                entity_config = light
                                entity_type = "light"
                                break

                        # Check if it's a switch
                        if not entity_config:
                            for switch in current_switches:
                                if switch.get(CONF_NAME) == entity_name:
                                    entity_config = switch
                                    entity_type = "switch"
                                    break

                        # Check if it's a cover
                        if not entity_config:
                            for cover in current_covers:
                                if cover.get(CONF_NAME) == entity_name:
                                    entity_config = cover
                                    entity_type = "cover"
                                    break

                        # Check if it's a binary sensor
                        if not entity_config:
                            for bs in current_binary_sensors:
                                if bs.get(CONF_NAME) == entity_name:
                                    entity_config = bs
                                    entity_type = "binary_sensor"
                                    break

                        # Check if it's a sensor
                        if not entity_config:
                            for s in current_sensors:
                                if s.get(CONF_NAME) == entity_name:
                                    entity_config = s
                                    entity_type = "sensor"
                                    break

                        # Check if it's a climate
                        if not entity_config:
                            for cl in current_climates:
                                if cl.get(CONF_NAME) == entity_name:
                                    entity_config = cl
                                    entity_type = "climate"
                                    break

                        # Check if it's a media player
                        if not entity_config:
                            for mp in current_media_players:
                                if mp.get(CONF_NAME) == entity_name:
                                    entity_config = mp
                                    entity_type = "media_player"
                                    break

                        if entity_config and entity_type:
                            # Construct unique_id based on entity type
                            if entity_type == "light":
                                brightness_join_str = entity_config.get(CONF_BRIGHTNESS_JOIN, "")
                                if brightness_join_str and brightness_join_str[0] == 'a':
                                    join_num = brightness_join_str[1:]
                                    unique_id = f"crestron_light_ui_a{join_num}"
                                else:
                                    continue
                            elif entity_type == "switch":
                                switch_join_str = entity_config.get(CONF_SWITCH_JOIN, "")
                                if switch_join_str and switch_join_str[0] == 'd':
                                    join_num = switch_join_str[1:]
                                    unique_id = f"crestron_switch_ui_d{join_num}"
                                else:
                                    continue
                            elif entity_type == "cover":
                                pos_join_str = entity_config.get(CONF_POS_JOIN, "")
                                if pos_join_str and pos_join_str[0] == 'a':
                                    join_num = pos_join_str[1:]
                                    unique_id = f"crestron_cover_ui_a{join_num}"
                                else:
                                    continue
                            elif entity_type == "binary_sensor":
                                is_on_join_str = entity_config.get(CONF_IS_ON_JOIN, "")
                                if is_on_join_str and is_on_join_str[0] == 'd':
                                    join_num = is_on_join_str[1:]
                                    unique_id = f"crestron_binary_sensor_ui_d{join_num}"
                                else:
                                    continue
                            elif entity_type == "sensor":
                                value_join_str = entity_config.get(CONF_VALUE_JOIN, "")
                                if value_join_str and value_join_str[0] == 'a':
                                    join_num = value_join_str[1:]
                                    unique_id = f"crestron_sensor_ui_a{join_num}"
                                else:
                                    continue
                            elif entity_type == "climate":
                                # Use setpoint join for floor warming
                                sp_join_str = entity_config.get(CONF_FLOOR_SP_JOIN, "")
                                if sp_join_str and sp_join_str[0] == 'a':
                                    join_num = sp_join_str[1:]
                                    unique_id = f"crestron_climate_ui_a{join_num}"
                                else:
                                    continue
                            elif entity_type == "media_player":
                                source_join_str = entity_config.get(CONF_SOURCE_NUM_JOIN, "")
                                if source_join_str and source_join_str[0] == 'a':
                                    join_num = source_join_str[1:]
                                    unique_id = f"crestron_media_player_ui_a{join_num}"
                                else:
                                    continue

                            # Find and remove entity from registry
                            entity_id = entity_reg.async_get_entity_id(
                                entity_type, DOMAIN, unique_id
                            )

                            if entity_id:
                                entity_reg.async_remove(entity_id)
                                removed_count += 1
                                _LOGGER.info(
                                    "Removed entity %s (unique_id: %s) from registry",
                                    entity_name, unique_id
                                )

                    # Reload the integration
                    await self._async_reload_integration()

                    _LOGGER.info(
                        "Removed %d entities from config, %d from registry",
                        len(entities_to_remove), removed_count
                    )

                # Return to menu
                return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error removing entities: %s", err)
                errors["base"] = "unknown"

        # Build list of all entities for removal selection
        current_covers = self.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
        current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
        current_climates = self.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

        entity_options = []
        for l in current_lights:
            entity_options.append({
                "label": f"{l.get(CONF_NAME)} (Light - {l.get(CONF_BRIGHTNESS_JOIN)})",
                "value": l.get(CONF_NAME)
            })
        for sw in current_switches:
            entity_options.append({
                "label": f"{sw.get(CONF_NAME)} (Switch - {sw.get(CONF_SWITCH_JOIN)})",
                "value": sw.get(CONF_NAME)
            })
        for c in current_covers:
            entity_options.append({
                "label": f"{c.get(CONF_NAME)} (Cover - {c.get(CONF_POS_JOIN)})",
                "value": c.get(CONF_NAME)
            })
        for bs in current_binary_sensors:
            entity_options.append({
                "label": f"{bs.get(CONF_NAME)} (Binary Sensor - {bs.get(CONF_IS_ON_JOIN)})",
                "value": bs.get(CONF_NAME)
            })
        for s in current_sensors:
            entity_options.append({
                "label": f"{s.get(CONF_NAME)} (Sensor - {s.get(CONF_VALUE_JOIN)})",
                "value": s.get(CONF_NAME)
            })
        for cl in current_climates:
            climate_type = cl.get(CONF_TYPE, "standard")
            type_label = "Floor Warming" if climate_type == "floor_warming" else "Standard HVAC"
            join_display = cl.get(CONF_FLOOR_SP_JOIN) if climate_type == "floor_warming" else cl.get(CONF_HEAT_SP_JOIN)
            entity_options.append({
                "label": f"{cl.get(CONF_NAME)} (Climate - {type_label} - {join_display})",
                "value": cl.get(CONF_NAME)
            })
        for mp in current_media_players:
            entity_options.append({
                "label": f"{mp.get(CONF_NAME)} (Media Player - {mp.get(CONF_SOURCE_NUM_JOIN)})",
                "value": mp.get(CONF_NAME)
            })

        if not entity_options:
            # No entities to remove, return to menu
            return await self.async_step_init()

        # Show removal form
        remove_schema = vol.Schema(
            {
                vol.Optional("entities_to_remove"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=entity_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="remove_entities",
            data_schema=remove_schema,
            errors=errors,
        )

    # ========== Dimmer/Keypad Configuration Methods ==========

    async def async_step_add_dimmer_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Basic dimmer information."""
        _LOGGER.debug("async_step_add_dimmer_basic called with user_input: %s", user_input)
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME, "").strip()
                button_count = int(user_input.get(CONF_BUTTON_COUNT, "4"))  # Convert string to int
                has_lighting_load = user_input.get("has_lighting_load", False)

                # Validate name
                if not name:
                    errors[CONF_NAME] = "name_required"

                # Check for duplicate dimmer name
                current_dimmers = self.config_entry.data.get(CONF_DIMMERS, [])
                if any(d.get(CONF_NAME) == name for d in current_dimmers):
                    errors[CONF_NAME] = "dimmer_name_exists"

                if not errors:
                    # Store temporary dimmer config
                    self._editing_join = {
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
        basic_schema = vol.Schema(
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

        return self.async_show_form(
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
                light_name = user_input.get("light_name", "").strip()
                is_on_join = user_input.get(CONF_IS_ON_JOIN, "").strip()
                has_brightness = user_input.get("has_brightness", False)
                brightness_join = user_input.get(CONF_BRIGHTNESS_JOIN, "").strip()

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
                    all_joins = [is_on_join]
                    if has_brightness and brightness_join:
                        all_joins.append(brightness_join)

                    conflict = self._check_join_conflicts(all_joins)
                    if conflict:
                        errors["base"] = f"join_conflict_{conflict}"

                if not errors:
                    # Store lighting load config
                    lighting_load = {
                        CONF_NAME: light_name,
                        CONF_IS_ON_JOIN: is_on_join,
                    }
                    if has_brightness and brightness_join:
                        lighting_load[CONF_BRIGHTNESS_JOIN] = brightness_join

                    self._editing_join[CONF_LIGHTING_LOAD] = lighting_load

                    # Move to button 1
                    return await self.async_step_add_dimmer_button(button_num=1)

            except Exception as ex:
                _LOGGER.exception("Unexpected error configuring lighting load: %s", ex)
                errors["base"] = "unknown"

        # Show lighting load form
        lighting_schema = vol.Schema(
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

        return self.async_show_form(
            step_id="add_dimmer_lighting",
            data_schema=lighting_schema,
            errors=errors,
            description_placeholders={
                "dimmer_name": self._editing_join.get(CONF_NAME, ""),
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
                button_config = {"number": button_num}

                # Press action
                config_press = user_input.get("config_press", False)
                press_join = user_input.get("press_join", "").strip()
                press_entity = user_input.get("press_entity")
                press_action = user_input.get("press_action")
                press_data = user_input.get("press_service_data", "").strip()

                # Double press action
                config_double = user_input.get("config_double_press", False)
                double_join = user_input.get("double_press_join", "").strip()
                double_entity = user_input.get("double_press_entity")
                double_action = user_input.get("double_press_action")
                double_data = user_input.get("double_service_data", "").strip()

                # Hold action
                config_hold = user_input.get("config_hold", False)
                hold_join = user_input.get("hold_join", "").strip()
                hold_entity = user_input.get("hold_entity")
                hold_action = user_input.get("hold_action")
                hold_data = user_input.get("hold_service_data", "").strip()

                # Feedback
                config_feedback = user_input.get("config_feedback", False)
                feedback_join = user_input.get("feedback_join", "").strip()
                feedback_entity = user_input.get("feedback_entity")

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
                    button_joins = []
                    if CONF_PRESS in button_config:
                        button_joins.append(button_config[CONF_PRESS]["join"])
                    if CONF_DOUBLE_PRESS in button_config:
                        button_joins.append(button_config[CONF_DOUBLE_PRESS]["join"])
                    if CONF_HOLD in button_config:
                        button_joins.append(button_config[CONF_HOLD]["join"])
                    if CONF_FEEDBACK in button_config:
                        button_joins.append(button_config[CONF_FEEDBACK]["join"])

                    conflict = self._check_join_conflicts(button_joins)
                    if conflict:
                        errors["base"] = f"join_conflict"

                if not errors:
                    # Add button to dimmer config
                    self._editing_join[CONF_BUTTONS].append(button_config)

                    # Check if we need more buttons
                    total_buttons = self._editing_join.get(CONF_BUTTON_COUNT, 0)
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
        total_buttons = self._editing_join.get(CONF_BUTTON_COUNT, 0)

        button_schema = vol.Schema(
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

        return self.async_show_form(
            step_id="add_dimmer_button",
            data_schema=button_schema,
            errors=errors,
            description_placeholders={
                "dimmer_name": self._editing_join.get(CONF_NAME, ""),
                "button_num": str(button_num),
                "total_buttons": str(total_buttons),
                "step": str(2 + button_num if self._editing_join.get(CONF_LIGHTING_LOAD) else 1 + button_num),
            },
        )

    async def _save_dimmer(self) -> FlowResult:
        """Save the dimmer configuration."""
        try:
            current_dimmers = self.config_entry.data.get(CONF_DIMMERS, []).copy()
            current_dimmers.append(self._editing_join)

            # Update config entry
            updated_data = {**self.config_entry.data, CONF_DIMMERS: current_dimmers}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=updated_data
            )

            _LOGGER.info(
                "Added dimmer '%s' with %s buttons",
                self._editing_join.get(CONF_NAME),
                self._editing_join.get(CONF_BUTTON_COUNT),
            )

            # Clear editing state
            self._editing_join = None

            # Reload integration
            await self._async_reload_integration()

            return self.async_create_entry(title="", data={})

        except Exception as ex:
            _LOGGER.exception("Failed to save dimmer: %s", ex)
            return self.async_abort(reason="save_failed")

    async def async_step_select_dimmer_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which dimmer to edit."""
        current_dimmers = self.config_entry.data.get(CONF_DIMMERS, [])

        if not current_dimmers:
            return self.async_abort(reason="no_dimmers_configured")

        if user_input is not None:
            dimmer_name = user_input.get("dimmer_to_edit")

            # Find the dimmer
            dimmer = next((d for d in current_dimmers if d.get(CONF_NAME) == dimmer_name), None)
            if dimmer:
                self._editing_join = dimmer.copy()
                return await self.async_step_edit_dimmer()

        # Build dimmer selection
        dimmer_options = [
            {"label": f"{d.get(CONF_NAME)} ({d.get(CONF_BUTTON_COUNT)} buttons)", "value": d.get(CONF_NAME)}
            for d in current_dimmers
        ]

        select_schema = vol.Schema(
            {
                vol.Required("dimmer_to_edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=dimmer_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="select_dimmer_to_edit",
            data_schema=select_schema,
        )

    async def async_step_edit_dimmer(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit an existing dimmer (full reconfiguration)."""
        if user_input is not None:
            # User chose to reconfigure
            # Start from beginning with current config pre-filled
            return await self.async_step_add_dimmer_basic()

        return self.async_show_menu(
            step_id="edit_dimmer",
            menu_options=["reconfigure", "back"],
            description_placeholders={
                "dimmer_name": self._editing_join.get(CONF_NAME, ""),
            },
        )

    async def async_step_remove_dimmers(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove selected dimmers."""
        errors: dict[str, str] = {}
        current_dimmers = self.config_entry.data.get(CONF_DIMMERS, [])

        if not current_dimmers:
            return self.async_abort(reason="no_dimmers_configured")

        if user_input is not None:
            try:
                dimmers_to_remove = user_input.get("dimmers_to_remove", [])

                if dimmers_to_remove:
                    # Filter out removed dimmers
                    updated_dimmers = [
                        d for d in current_dimmers
                        if d.get(CONF_NAME) not in dimmers_to_remove
                    ]

                    # Update config entry
                    updated_data = {**self.config_entry.data, CONF_DIMMERS: updated_dimmers}
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=updated_data
                    )

                    # Clean up entities generated by these dimmers
                    for dimmer_name in dimmers_to_remove:
                        dimmer = next((d for d in current_dimmers if d.get(CONF_NAME) == dimmer_name), None)
                        if dimmer:
                            # Remove all entities and device from registry
                            await self._cleanup_dimmer_entities(dimmer)

                    _LOGGER.info("Removed %s dimmer(s)", len(dimmers_to_remove))

                    # Reload integration
                    await self._async_reload_integration()

                return self.async_create_entry(title="", data={})

            except Exception as ex:
                _LOGGER.exception("Unexpected error removing dimmers: %s", ex)
                errors["base"] = "unknown"

        # Build dimmer options
        dimmer_options = [
            {"label": f"{d.get(CONF_NAME)} ({d.get(CONF_BUTTON_COUNT)} buttons)", "value": d.get(CONF_NAME)}
            for d in current_dimmers
        ]

        # Show removal form
        remove_schema = vol.Schema(
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

        return self.async_show_form(
            step_id="remove_dimmers",
            data_schema=remove_schema,
            errors=errors,
        )

    def _check_join_conflicts(self, new_joins: list[str]) -> str | None:
        """Check if any joins conflict with existing configuration."""
        # Check against all existing joins (to_joins, from_joins, entities, other dimmers)
        current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])
        current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
        current_covers = self.config_entry.data.get(CONF_COVERS, [])
        current_dimmers = self.config_entry.data.get(CONF_DIMMERS, [])

        used_joins = set()

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
        entity_reg = er.async_get(self.hass)
        device_reg = dr.async_get(self.hass)

        dimmer_name = dimmer.get(CONF_NAME)
        button_count = dimmer.get(CONF_BUTTON_COUNT, 2)
        base_join = dimmer.get(CONF_BASE_JOIN)
        manual_joins = dimmer.get("manual_joins")

        _LOGGER.debug("Cleaning up dimmer '%s' with %d buttons", dimmer_name, button_count)

        # Remove event entities (one per button)
        for button_num in range(1, button_count + 1):
            unique_id = f"crestron_event_{dimmer_name}_button_{button_num}"
            entity_id = entity_reg.async_get_entity_id("event", DOMAIN, unique_id)
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
            if manual_joins and button_num in manual_joins:
                press_join_str = manual_joins[button_num]["press"]
                press_join = int(press_join_str[1:])
            else:
                # Auto-sequential mode
                base_offset = (button_num - 1) * 3
                press_join = int(base_join[1:]) + base_offset

            unique_id = f"crestron_led_{dimmer_name}_d{press_join}"
            entity_id = entity_reg.async_get_entity_id("switch", DOMAIN, unique_id)
            if entity_id:
                _LOGGER.debug("Removing LED switch entity: %s", entity_id)
                entity_reg.async_remove(entity_id)

        # Remove lighting load entity if present
        if dimmer.get(CONF_HAS_LIGHTING_LOAD):
            brightness_join_str = dimmer.get(CONF_LIGHT_BRIGHTNESS_JOIN)
            if brightness_join_str:
                brightness_join = int(brightness_join_str[1:])  # Remove 'a' prefix
                unique_id = f"crestron_light_dimmer_{dimmer_name}_a{brightness_join}"
                entity_id = entity_reg.async_get_entity_id("light", DOMAIN, unique_id)
                if entity_id:
                    _LOGGER.debug("Removing dimmer light entity: %s", entity_id)
                    entity_reg.async_remove(entity_id)

        # Remove the device from device registry
        device_identifier = (DOMAIN, f"dimmer_{dimmer_name}")
        device = device_reg.async_get_device(identifiers={device_identifier})
        if device:
            _LOGGER.debug("Removing device: %s", dimmer_name)
            device_reg.async_remove_device(device.id)


class PortInUse(HomeAssistantError):
    """Error to indicate port is already in use."""


class InvalidPort(HomeAssistantError):
    """Error to indicate port is invalid."""
