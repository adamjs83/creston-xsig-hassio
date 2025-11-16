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
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_PORT, CONF_TO_HUB, CONF_FROM_HUB

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
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Main menu for managing joins."""
        if user_input is not None:
            # Handle menu selection
            next_step = user_input.get("action")
            if next_step == "add_to_join":
                return await self.async_step_add_to_join()
            elif next_step == "add_from_join":
                return await self.async_step_add_from_join()
            elif next_step == "remove_joins":
                return await self.async_step_remove_joins()
            else:
                # Done
                return self.async_create_entry(title="", data={})

        # Get current counts
        current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])

        # Show menu
        menu_schema = vol.Schema(
            {
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": f"Add to_join (HA→Crestron) - Currently: {len(current_to_joins)}", "value": "add_to_join"},
                            {"label": f"Add from_join (Crestron→HA) - Currently: {len(current_from_joins)}", "value": "add_from_join"},
                            {"label": "Remove joins", "value": "remove_joins"},
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
        )

    async def async_step_add_to_join(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a single to_join with entity picker."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                join_num = user_input.get("join")
                entity_id = user_input.get("entity_id")
                attribute = user_input.get("attribute", "").strip()
                value_template = user_input.get("value_template", "").strip()

                # Validate join format
                if not join_num or not (join_num[0] in ['d', 'a', 's'] and join_num[1:].isdigit()):
                    errors["join"] = "invalid_join_format"

                # Check for duplicate join
                current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
                if any(j.get("join") == join_num for j in current_to_joins):
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

                    # Append to existing to_joins
                    updated_to_joins = current_to_joins + [new_join]

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_TO_HUB] = updated_to_joins

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                    _LOGGER.info("Added to_join %s for %s", join_num, entity_id)

                    # Return to menu
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding to_join: %s", err)
                errors["base"] = "unknown"

        # Show form
        add_to_join_schema = vol.Schema(
            {
                vol.Required("join"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional("entity_id"): selector.EntitySelector(),
                vol.Optional("attribute"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional("value_template"): selector.TextSelector(
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
        """Add a single from_join."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                join_num = user_input.get("join")
                service = user_input.get("service")
                target_entity = user_input.get("target_entity")

                # Validate join format
                if not join_num or not (join_num[0] in ['d', 'a', 's'] and join_num[1:].isdigit()):
                    errors["join"] = "invalid_join_format"

                # Check for duplicate join
                current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])
                if any(j.get("join") == join_num for j in current_from_joins):
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

                    # Append to existing from_joins
                    updated_from_joins = current_from_joins + [new_join]

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_FROM_HUB] = updated_from_joins

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                    _LOGGER.info("Added from_join %s with service %s", join_num, service)

                    # Return to menu
                    return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding from_join: %s", err)
                errors["base"] = "unknown"

        # Show form
        add_from_join_schema = vol.Schema(
            {
                vol.Required("join"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required("service"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional("target_entity"): selector.EntitySelector(),
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
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

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


class PortInUse(HomeAssistantError):
    """Error to indicate port is already in use."""


class InvalidPort(HomeAssistantError):
    """Error to indicate port is invalid."""
