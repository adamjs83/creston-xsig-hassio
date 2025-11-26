"""Base classes and utilities for Crestron XSIG config flow."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_LOGGER: logging.Logger = logging.getLogger(__name__)


class BaseOptionsFlow(config_entries.OptionsFlow):
    """Base class for options flow handlers."""

    _editing_join: int | None

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.

        Args:
            config_entry: The config entry being configured
        """
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


class EntityConfigHelper:
    """Helper class for entity configuration operations."""

    hass: HomeAssistant
    config_entry: config_entries.ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize entity config helper.

        Args:
            hass: Home Assistant instance
            config_entry: The config entry
        """
        self.hass = hass
        self.config_entry = config_entry

    async def cleanup_entity(self, platform: str, unique_id: str) -> None:
        """Remove entity from entity registry.

        Args:
            platform: Platform name (e.g., "cover", "light")
            unique_id: Unique ID of entity to remove
        """
        from ..const import DOMAIN

        entity_reg = er.async_get(self.hass)
        entity_id = entity_reg.async_get_entity_id(platform, DOMAIN, unique_id)
        if entity_id:
            entity_reg.async_remove(entity_id)
            _LOGGER.debug("Removed %s entity %s from registry", platform, entity_id)

    def check_duplicate_name(
        self, entities_list: list[dict[str, Any]], new_name: str, exclude_index: int | None = None
    ) -> bool:
        """Check if entity name already exists in list.

        Args:
            entities_list: List of entity configurations
            new_name: Name to check
            exclude_index: Index to exclude from check (when editing)

        Returns:
            True if duplicate found, False otherwise
        """
        from homeassistant.const import CONF_NAME

        for idx, entity in enumerate(entities_list):
            if exclude_index is not None and idx == exclude_index:
                continue
            if entity.get(CONF_NAME) == new_name:
                return True
        return False
