"""Helper functions for Crestron integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .const import DOMAIN, HUB

_LOGGER = logging.getLogger(__name__)


def get_hub(
    hass: HomeAssistant,
    entry: ConfigEntry | None = None,
) -> Any | None:
    """Get the Crestron hub from hass.data.

    For config entry setup: tries entry-specific data first, falls back to YAML hub.
    For YAML setup (entry=None): gets from global HUB key.

    Args:
        hass: Home Assistant instance
        entry: Config entry (optional, for entry-specific hub lookup)

    Returns:
        The hub instance or None if not found
    """
    if DOMAIN not in hass.data:
        return None

    if entry is not None:
        entry_data = hass.data[DOMAIN].get(entry.entry_id)
        if entry_data:
            if isinstance(entry_data, dict):
                hub = entry_data.get(HUB)
            else:
                hub = entry_data
            if hub:
                return hub

    # Fall back to global HUB key (YAML setup or shared hub)
    return hass.data[DOMAIN].get(HUB)


def get_hub_wrapper(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> Any | None:
    """Get the hub wrapper (CrestronHub instance) from entry data.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        The hub wrapper instance or None if not found
    """
    if DOMAIN not in hass.data:
        return None

    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data and isinstance(entry_data, dict):
        return entry_data.get("hub_wrapper")

    return None
