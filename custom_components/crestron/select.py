"""Support for Crestron LED binding select entities."""
import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    HUB,
    CONF_DIMMERS,
    CONF_BASE_JOIN,
    CONF_BUTTON_COUNT,
    BINDABLE_DOMAINS,
    STATE_TO_LED,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crestron LED binding select entities from a config entry."""
    hub = hass.data[DOMAIN][HUB]
    dimmers = config_entry.data.get(CONF_DIMMERS, [])

    if not dimmers:
        return

    entities = []
    for dimmer in dimmers:
        dimmer_name = dimmer.get(CONF_NAME, "Unknown")
        base_join = dimmer.get(CONF_BASE_JOIN)
        button_count = dimmer.get(CONF_BUTTON_COUNT, 2)

        _LOGGER.debug(
            "Creating LED binding select entities for dimmer '%s' (%d buttons)",
            dimmer_name,
            button_count,
        )

        # Create LED binding select entities (1 per button)
        for button_num in range(1, button_count + 1):
            # Calculate LED entity ID (matches switch.py)
            led_entity_id = f"switch.{dimmer_name}_led_{button_num}".lower().replace(" ", "_")

            entity = CrestronLEDBinding(
                hass=hass,
                hub=hub,
                dimmer_name=dimmer_name,
                button_num=button_num,
                led_entity_id=led_entity_id,
            )
            entities.append(entity)

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d LED binding select entities", len(entities))


class CrestronLEDBinding(SelectEntity):
    """Representation of a Crestron LED binding select entity."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        hub,
        dimmer_name: str,
        button_num: int,
        led_entity_id: str,
    ) -> None:
        """Initialize the LED binding select entity."""
        self.hass = hass
        self._hub = hub
        self._dimmer_name = dimmer_name
        self._button_num = button_num
        self._led_entity_id = led_entity_id
        self._bound_entity = None
        self._state_listener = None

        # Entity naming
        self._attr_name = f"LED {button_num} Binding"
        self._attr_unique_id = f"crestron_led_binding_{dimmer_name}_button_{button_num}"

        # Initial options (will be updated in async_added_to_hass)
        self._attr_options = ["none"]
        self._attr_current_option = "none"

        # Device info (group under dimmer device)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"dimmer_{dimmer_name}")},
            "name": dimmer_name,
            "manufacturer": "Crestron",
            "model": "Keypad/Dimmer",
        }

    async def async_added_to_hass(self) -> None:
        """Update options when entity is added."""
        await self._update_options()

    async def _update_options(self) -> None:
        """Update the list of bindable entities."""
        entity_reg = er.async_get(self.hass)
        options = ["none"]

        # Scan all entities in HA
        for entity_id, entry in entity_reg.entities.items():
            # Skip this LED and other binding selects
            if entity_id == self._led_entity_id or "led_binding" in entity_id:
                continue

            # Only include bindable domains
            domain = entry.domain
            if domain in BINDABLE_DOMAINS:
                if not entry.disabled:
                    options.append(entity_id)

        self._attr_options = sorted(options)
        _LOGGER.debug(
            "LED %d binding: %d bindable entities available",
            self._button_num,
            len(options) - 1,  # Exclude 'none'
        )

    async def async_select_option(self, option: str) -> None:
        """Handle selection of binding option."""
        # Remove previous listener if exists
        if self._state_listener:
            self._state_listener()
            self._state_listener = None
            _LOGGER.debug("Removed previous state listener for LED %d", self._button_num)

        self._attr_current_option = option
        self._bound_entity = option if option != "none" else None

        # Register new listener if not 'none'
        if self._bound_entity:
            self._state_listener = async_track_state_change_event(
                self.hass,
                [self._bound_entity],
                self._handle_bound_state_change,
            )
            _LOGGER.info(
                "LED %d now bound to %s", self._button_num, self._bound_entity
            )

            # Immediately sync current state
            await self._sync_led_state()
        else:
            _LOGGER.info("LED %d binding removed", self._button_num)

        self.async_write_ha_state()

    @callback
    async def _handle_bound_state_change(self, event: Event) -> None:
        """Handle state change of bound entity."""
        await self._sync_led_state()

    async def _sync_led_state(self) -> None:
        """Sync LED state based on bound entity state."""
        if not self._bound_entity:
            return

        # Get current state of bound entity
        state = self.hass.states.get(self._bound_entity)
        if not state:
            return

        # Map state to LED on/off
        state_value = state.state
        should_be_on = STATE_TO_LED.get(state_value, False)

        _LOGGER.debug(
            "LED %d sync: %s is '%s' → LED %s",
            self._button_num,
            self._bound_entity,
            state_value,
            "ON" if should_be_on else "OFF",
        )

        # Update LED via Home Assistant service call
        service = "turn_on" if should_be_on else "turn_off"
        await self.hass.services.async_call(
            "switch",
            service,
            {"entity_id": self._led_entity_id},
            blocking=True,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when entity is removed."""
        if self._state_listener:
            self._state_listener()
            self._state_listener = None
