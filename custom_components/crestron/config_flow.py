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
from homeassistant.helpers import selector, entity_registry as er

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
        """Main menu - choose between entity or join sync management."""
        if user_input is not None:
            next_step = user_input.get("action")
            if next_step == "entity_menu":
                return await self.async_step_entity_menu()
            elif next_step == "join_menu":
                return await self.async_step_join_menu()
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
        total_entities = len(current_covers) + len(current_binary_sensors) + len(current_sensors) + len(current_lights) + len(current_switches) + len(current_climates)

        current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])
        total_joins = len(current_to_joins) + len(current_from_joins)

        # Show main menu
        menu_schema = vol.Schema(
            {
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": f"Manage Entities ({total_entities} configured)", "value": "entity_menu"},
                            {"label": f"Manage Join Syncs ({total_joins} configured)", "value": "join_menu"},
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
        total_entities = len(current_covers) + len(current_binary_sensors) + len(current_sensors) + len(current_lights) + len(current_switches) + len(current_climates)

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
            elif entity_type == "back":
                return await self.async_step_entity_menu()

        # Get current counts
        current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
        current_covers = self.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
        current_climates = self.config_entry.data.get(CONF_CLIMATES, [])

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

            # Not found, return to menu
            return await self.async_step_init()

        # Build list of all entities for editing
        current_covers = self.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.config_entry.data.get(CONF_SENSORS, [])
        current_lights = self.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.config_entry.data.get(CONF_SWITCHES, [])
        current_climates = self.config_entry.data.get(CONF_CLIMATES, [])

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

                    # Filter out selected entities
                    updated_covers = [c for c in current_covers if c.get(CONF_NAME) not in entities_to_remove]
                    updated_binary_sensors = [bs for bs in current_binary_sensors if bs.get(CONF_NAME) not in entities_to_remove]
                    updated_sensors = [s for s in current_sensors if s.get(CONF_NAME) not in entities_to_remove]
                    updated_lights = [l for l in current_lights if l.get(CONF_NAME) not in entities_to_remove]
                    updated_switches = [sw for sw in current_switches if sw.get(CONF_NAME) not in entities_to_remove]
                    updated_climates = [cl for cl in current_climates if cl.get(CONF_NAME) not in entities_to_remove]

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_COVERS] = updated_covers
                    new_data[CONF_BINARY_SENSORS] = updated_binary_sensors
                    new_data[CONF_SENSORS] = updated_sensors
                    new_data[CONF_LIGHTS] = updated_lights
                    new_data[CONF_SWITCHES] = updated_switches
                    new_data[CONF_CLIMATES] = updated_climates

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


class PortInUse(HomeAssistantError):
    """Error to indicate port is already in use."""


class InvalidPort(HomeAssistantError):
    """Error to indicate port is invalid."""
