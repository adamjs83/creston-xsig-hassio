"""Validation utilities for Crestron XSIG config flow."""
import logging
import socket
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ..const import CONF_PORT, DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__name__)

# Port validation schema
STEP_USER_DATA_SCHEMA: vol.Schema = vol.Schema(
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
                "Port %d is in use by YAML configuration. "
                "Config entry will be created but YAML will take precedence.",
                port
            )

    # Only check port availability if NOT used by our YAML config
    if not yaml_using_port:
        # Check if port is already in use by testing if we can bind to it
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", port))
        except OSError as err:
            _LOGGER.error("Port %d is already in use by external service: %s", port, err)
            raise PortInUse(f"Port {port} is already in use") from err

    return {"title": f"Crestron XSIG (Port {port})"}


class PortInUse(HomeAssistantError):
    """Error to indicate port is already in use."""


class InvalidPort(HomeAssistantError):
    """Error to indicate port is invalid."""
