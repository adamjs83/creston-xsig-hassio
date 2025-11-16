"""Config flow for Crestron XSIG integration."""
import logging
import socket
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_PORT

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

    # Options flow removed for v1.6.0 - no options to configure yet
    # Will be added in v1.7.0+ when entity configuration via UI is implemented


class PortInUse(HomeAssistantError):
    """Error to indicate port is already in use."""


class InvalidPort(HomeAssistantError):
    """Error to indicate port is invalid."""
