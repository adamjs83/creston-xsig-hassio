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
        """Manage the options for to_joins and from_joins."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Parse to_joins YAML
                to_joins = None
                if user_input.get("to_joins_yaml", "").strip():
                    try:
                        to_joins = yaml.safe_load(user_input["to_joins_yaml"])
                        if to_joins is not None and not isinstance(to_joins, list):
                            errors["to_joins_yaml"] = "invalid_yaml_format"
                    except yaml.YAMLError as err:
                        _LOGGER.error("Invalid YAML in to_joins: %s", err)
                        errors["to_joins_yaml"] = "invalid_yaml"

                # Parse from_joins YAML
                from_joins = None
                if user_input.get("from_joins_yaml", "").strip():
                    try:
                        from_joins = yaml.safe_load(user_input["from_joins_yaml"])
                        if from_joins is not None and not isinstance(from_joins, list):
                            errors["from_joins_yaml"] = "invalid_yaml_format"
                    except yaml.YAMLError as err:
                        _LOGGER.error("Invalid YAML in from_joins: %s", err)
                        errors["from_joins_yaml"] = "invalid_yaml"

                # If no errors, update the config entry
                if not errors:
                    # Build new data dict
                    new_data = {CONF_PORT: self.config_entry.data[CONF_PORT]}

                    if to_joins is not None:
                        new_data[CONF_TO_HUB] = to_joins
                        _LOGGER.info("Updated to_joins: %d entries", len(to_joins))

                    if from_joins is not None:
                        new_data[CONF_FROM_HUB] = from_joins
                        _LOGGER.info("Updated from_joins: %d entries", len(from_joins))

                    # Update config entry
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    # Reload the integration to apply changes
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                    return self.async_create_entry(title="", data={})

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in options flow: %s", err)
                errors["base"] = "unknown"

        # Get current values as YAML strings
        current_to_joins = self.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.config_entry.data.get(CONF_FROM_HUB, [])

        # Format as proper YAML with explicit style settings
        to_joins_yaml = yaml.dump(
            current_to_joins,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            explicit_start=False,
            width=1000,  # Prevent line wrapping
        ) if current_to_joins else ""

        from_joins_yaml = yaml.dump(
            current_from_joins,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            explicit_start=False,
            width=1000,  # Prevent line wrapping
        ) if current_from_joins else ""

        # Show form
        options_schema = vol.Schema(
            {
                vol.Optional(
                    "to_joins_yaml",
                    description={"suggested_value": to_joins_yaml},
                ): str,
                vol.Optional(
                    "from_joins_yaml",
                    description={"suggested_value": from_joins_yaml},
                ): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={
                "to_joins_count": str(len(current_to_joins)),
                "from_joins_count": str(len(current_from_joins)),
            },
        )


class PortInUse(HomeAssistantError):
    """Error to indicate port is already in use."""


class InvalidPort(HomeAssistantError):
    """Error to indicate port is invalid."""
