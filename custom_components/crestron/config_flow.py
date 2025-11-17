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

from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_TO_HUB,
    CONF_FROM_HUB,
    CONF_COVERS,
    CONF_POS_JOIN,
    CONF_IS_OPENING_JOIN,
    CONF_IS_CLOSING_JOIN,
    CONF_IS_CLOSED_JOIN,
    CONF_STOP_JOIN,
)
from homeassistant.const import CONF_NAME, CONF_TYPE

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
        self._editing_join = None  # Track which join we're editing
        self._import_summary = ""  # Store import summary for display

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
        """Main menu for managing joins."""
        if user_input is not None:
            # Handle menu selection
            next_step = user_input.get("action")
            if next_step == "add_cover":
                self._editing_join = None  # Clear editing state
                return await self.async_step_add_cover()
            elif next_step == "import_yaml_covers":
                return await self.async_step_import_yaml_covers()
            elif next_step == "add_to_join":
                self._editing_join = None  # Clear editing state
                return await self.async_step_add_to_join()
            elif next_step == "add_from_join":
                self._editing_join = None  # Clear editing state
                return await self.async_step_add_from_join()
            elif next_step == "edit_joins":
                return await self.async_step_select_join_to_edit()
            elif next_step == "edit_entities":
                return await self.async_step_select_entity_to_edit()
            elif next_step == "remove_joins":
                return await self.async_step_remove_joins()
            elif next_step == "remove_entities":
                return await self.async_step_remove_entities()
            else:
                # Done
                return self.async_create_entry(title="", data={})

        # Get current counts
        current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])
        current_covers = self.config_entry.data.get(CONF_COVERS, [])

        # Show menu
        menu_schema = vol.Schema(
            {
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": f"Add Cover - Currently: {len(current_covers)}", "value": "add_cover"},
                            {"label": "Import YAML Covers", "value": "import_yaml_covers"},
                            {"label": f"Add to_join (HA→Crestron) - Currently: {len(current_to_joins)}", "value": "add_to_join"},
                            {"label": f"Add from_join (Crestron→HA) - Currently: {len(current_from_joins)}", "value": "add_from_join"},
                            {"label": "Edit joins", "value": "edit_joins"},
                            {"label": "Edit entities", "value": "edit_entities"},
                            {"label": "Remove joins", "value": "remove_joins"},
                            {"label": "Remove entities", "value": "remove_entities"},
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

    async def async_step_select_entity_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which entity to edit."""
        if user_input is not None:
            selected_entity = user_input.get("entity_to_edit")

            if selected_entity:
                # Find the entity in our data
                current_covers = self.config_entry.data.get(CONF_COVERS, [])

                # Check if it's a cover
                for cover in current_covers:
                    if cover.get(CONF_NAME) == selected_entity:
                        self._editing_join = cover
                        return await self.async_step_add_cover()

            # Not found, return to menu
            return await self.async_step_init()

        # Build list of all entities for editing
        current_covers = self.config_entry.data.get(CONF_COVERS, [])

        entity_options = []
        for c in current_covers:
            entity_options.append({
                "label": f"{c.get(CONF_NAME)} (Cover - {c.get(CONF_POS_JOIN)})",
                "value": c.get(CONF_NAME)
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

                    # Filter out selected entities
                    updated_covers = [c for c in current_covers if c.get(CONF_NAME) not in entities_to_remove]

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_COVERS] = updated_covers

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self._async_reload_integration()

                    _LOGGER.info("Removed %d entities", len(entities_to_remove))

                # Return to menu
                return await self.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error removing entities: %s", err)
                errors["base"] = "unknown"

        # Build list of all entities for removal selection
        current_covers = self.config_entry.data.get(CONF_COVERS, [])

        entity_options = []
        for c in current_covers:
            entity_options.append({
                "label": f"{c.get(CONF_NAME)} (Cover - {c.get(CONF_POS_JOIN)})",
                "value": c.get(CONF_NAME)
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

    async def async_step_import_yaml_covers(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Import covers from YAML configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                yaml_text = user_input.get("yaml_config", "").strip()

                if not yaml_text:
                    errors["yaml_config"] = "empty_yaml"
                else:
                    # Remove common leading whitespace (dedent)
                    # Users copy from YAML where list is indented under "cover:"
                    import textwrap
                    yaml_text = textwrap.dedent(yaml_text)

                    # Parse YAML
                    try:
                        yaml_data = yaml.safe_load(yaml_text)
                    except yaml.YAMLError as err:
                        _LOGGER.error("YAML parse error: %s", err)
                        errors["yaml_config"] = "invalid_yaml"
                        yaml_data = None

                    if yaml_data and not errors:
                        # Handle different YAML formats:
                        # 1. List of covers: [- platform: crestron, ...]
                        # 2. Single cover: {platform: crestron, ...}
                        # 3. Wrapped in "cover:" key: {cover: [- platform: crestron, ...]}
                        if isinstance(yaml_data, dict):
                            # Check if it's wrapped in "cover:" key
                            if "cover" in yaml_data:
                                yaml_data = yaml_data["cover"]
                            else:
                                # Single cover dict
                                yaml_data = [yaml_data]

                        # Ensure it's a list at this point
                        if not isinstance(yaml_data, list):
                            yaml_data = [yaml_data]

                        imported_covers = []
                        skipped_covers = []
                        current_covers = self.config_entry.data.get(CONF_COVERS, [])

                        for cover_yaml in yaml_data:
                            # Skip if not a crestron cover
                            if cover_yaml.get("platform") != "crestron":
                                continue

                            name = cover_yaml.get("name")
                            if not name:
                                skipped_covers.append("(unnamed cover)")
                                continue

                            # Check if already exists
                            if any(c.get(CONF_NAME) == name for c in current_covers):
                                skipped_covers.append(f"{name} (already exists)")
                                continue

                            # Convert YAML format to UI format
                            # YAML uses integer joins, UI uses string format
                            pos_join = cover_yaml.get("pos_join")
                            if pos_join is None:
                                skipped_covers.append(f"{name} (no pos_join)")
                                continue

                            new_cover = {
                                CONF_NAME: name,
                                CONF_POS_JOIN: f"a{pos_join}",
                                CONF_TYPE: cover_yaml.get("type", "shade"),
                            }

                            # Add optional joins
                            if "is_opening_join" in cover_yaml:
                                new_cover[CONF_IS_OPENING_JOIN] = f"d{cover_yaml['is_opening_join']}"
                            if "is_closing_join" in cover_yaml:
                                new_cover[CONF_IS_CLOSING_JOIN] = f"d{cover_yaml['is_closing_join']}"
                            if "is_closed_join" in cover_yaml:
                                new_cover[CONF_IS_CLOSED_JOIN] = f"d{cover_yaml['is_closed_join']}"
                            if "stop_join" in cover_yaml:
                                new_cover[CONF_STOP_JOIN] = f"d{cover_yaml['stop_join']}"

                            imported_covers.append(new_cover)

                        if imported_covers:
                            # Add imported covers to config entry
                            updated_covers = current_covers + imported_covers

                            new_data = dict(self.config_entry.data)
                            new_data[CONF_COVERS] = updated_covers

                            self.hass.config_entries.async_update_entry(
                                self.config_entry, data=new_data
                            )

                            # Reload the integration
                            await self._async_reload_integration()

                            _LOGGER.info(
                                "Imported %d covers, skipped %d",
                                len(imported_covers),
                                len(skipped_covers)
                            )

                            # Show success message
                            import_summary = f"Successfully imported {len(imported_covers)} cover(s)."
                            if skipped_covers:
                                import_summary += f"\n\nSkipped {len(skipped_covers)}:\n" + "\n".join(skipped_covers)

                            # Store summary for display
                            self._import_summary = import_summary

                            # Show summary step
                            return await self.async_step_import_summary()
                        else:
                            errors["yaml_config"] = "no_covers_found"

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error importing YAML covers: %s", err)
                errors["base"] = "unknown"

        # Show form
        import_schema = vol.Schema(
            {
                vol.Required("yaml_config"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="import_yaml_covers",
            data_schema=import_schema,
            errors=errors,
        )

    async def async_step_import_summary(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show summary of imported covers."""
        if user_input is not None:
            # Return to menu
            return await self.async_step_init()

        # Show summary with OK button
        return self.async_show_form(
            step_id="import_summary",
            data_schema=vol.Schema({}),
            description_placeholders={"summary": self._import_summary},
        )


class PortInUse(HomeAssistantError):
    """Error to indicate port is already in use."""


class InvalidPort(HomeAssistantError):
    """Error to indicate port is invalid."""
