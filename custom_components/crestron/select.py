"""Support for Crestron LED binding select entities.

DEPRECATED (v1.20.8): LED binding is now handled via blueprint automations.
This module only handles cleanup of orphaned entities from older versions.
"""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Clean up deprecated LED binding select entities.

    DEPRECATED (v1.20.8): LED binding is now handled directly in the blueprint.
    This function only cleans up orphaned LED binding entities from the registry.
    """
    # Clean up deprecated LED binding select entities from entity registry
    entity_reg: er.EntityRegistry = er.async_get(hass)
    removed_count: int = 0

    # Find and remove all LED binding select entities for this domain
    entities_to_remove: list[str] = []
    for entity_id, entry in entity_reg.entities.items():
        if (
            entry.domain == "select"
            and entry.platform == DOMAIN
            and "led_binding" in (entry.unique_id or "")
        ):
            entities_to_remove.append(entity_id)

    for entity_id in entities_to_remove:
        _LOGGER.info("Removing deprecated LED binding entity: %s", entity_id)
        entity_reg.async_remove(entity_id)
        removed_count += 1

    if removed_count > 0:
        _LOGGER.info(
            "Cleaned up %d deprecated LED binding select entities. "
            "LED binding is now configured via blueprint automations.",
            removed_count,
        )
