"""Support for Crestron button press events."""
import logging
from typing import Any

from homeassistant.components.event import (
    EventEntity,
    EventDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    HUB,
    CONF_DIMMERS,
    CONF_BASE_JOIN,
    CONF_BUTTON_COUNT,
    ENTITY_TYPE_BUTTON_EVENT,
)

_LOGGER = logging.getLogger(__name__)

# Event types that button entities can fire
EVENT_TYPES = ["press", "double_press", "hold"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crestron button event entities from a config entry."""
    # Get hub for this specific config entry (supports multiple hubs)
    hub_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if hub_data:
        # Hub data is stored as dict with HUB key
        if isinstance(hub_data, dict):
            hub = hub_data.get(HUB)
        else:
            hub = hub_data  # Fallback for direct hub reference
    else:
        # Fallback to global HUB key (for single hub setups)
        hub = hass.data[DOMAIN].get(HUB)

    if hub is None:
        _LOGGER.error("No Crestron hub found for event entities")
        return

    dimmers = config_entry.data.get(CONF_DIMMERS, [])

    if not dimmers:
        return

    entities = []
    for dimmer in dimmers:
        dimmer_name = dimmer.get(CONF_NAME, "Unknown")
        base_join = dimmer.get(CONF_BASE_JOIN)
        manual_joins = dimmer.get("manual_joins")
        button_count = dimmer.get(CONF_BUTTON_COUNT, 2)

        mode = "manual" if manual_joins else "auto-sequential"
        _LOGGER.debug(
            "Creating button event entities for dimmer '%s' (%s mode, %d buttons)",
            dimmer_name,
            mode,
            button_count,
        )

        # Create button event entities (1 per button)
        # Each button fires 3 event types: press, double_press, hold
        for button_num in range(1, button_count + 1):
            # Get joins for this button (manual or auto-sequential)
            if manual_joins and button_num in manual_joins:
                # Manual mode: use explicitly configured joins
                press_join = manual_joins[button_num]["press"]
                double_join = manual_joins[button_num]["double"]
                hold_join = manual_joins[button_num]["hold"]
            else:
                # Auto-sequential mode: calculate from base join
                # Button 1: d10 (press), d11 (double), d12 (hold)
                # Button 2: d13 (press), d14 (double), d15 (hold)
                base_offset = (button_num - 1) * 3
                press_join_num = int(base_join[1:]) + base_offset
                press_join = f"d{press_join_num}"
                double_join = f"d{press_join_num + 1}"
                hold_join = f"d{press_join_num + 2}"

            entity = CrestronButtonEvent(
                hub=hub,
                dimmer_name=dimmer_name,
                button_num=button_num,
                press_join=press_join,
                double_join=double_join,
                hold_join=hold_join,
            )
            entities.append(entity)

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d button event entities", len(entities))


class CrestronButtonEvent(EventEntity):
    """Representation of a Crestron button event entity."""

    _attr_event_types = EVENT_TYPES
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_has_entity_name = True

    def __init__(
        self,
        hub,
        dimmer_name: str,
        button_num: int,
        press_join: str,
        double_join: str,
        hold_join: str,
    ) -> None:
        """Initialize the button event entity."""
        self._hub = hub
        self._dimmer_name = dimmer_name
        self._button_num = button_num
        self._press_join = press_join
        self._double_join = double_join
        self._hold_join = hold_join
        self._name = f"Button {button_num}"

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self):
        """Return unique ID for the entity."""
        return f"crestron_event_{self._dimmer_name}_button_{self._button_num}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"dimmer_{self._dimmer_name}")},
            name=self._dimmer_name,
            manufacturer="Crestron",
            model="Keypad/Dimmer",
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        # Register single global callback (hub doesn't support join-specific callbacks)
        self._hub.register_callback(self.process_callback)

        _LOGGER.debug(
            "Registered button %d event listeners: %s (press), %s (double), %s (hold)",
            self._button_num,
            self._press_join,
            self._double_join,
            self._hold_join,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks when entity is removed."""
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype: str, value: str) -> None:
        """Process hub callback and check if it's for one of our joins."""
        # cbtype format: "d2" for digital join 2, "a5" for analog join 5, etc.
        # Check if this callback is for one of our monitored joins
        if cbtype == self._press_join:
            self._handle_press(value)
        elif cbtype == self._double_join:
            self._handle_double_press(value)
        elif cbtype == self._hold_join:
            self._handle_hold(value)

    @callback
    def _handle_press(self, value: str) -> None:
        """Handle press join trigger."""
        if value == "1":  # Digital high = button pressed
            event_data = {
                "device_name": self._dimmer_name,
                "button": self._button_num,
                "action": "press",
            }

            # Fire EventEntity event (updates entity state)
            self._trigger_event("press", event_data)

            # Fire event on the bus for automations
            self.hass.bus.async_fire("crestron_button", event_data)

            _LOGGER.debug(
                "%s button %d: press event", self._dimmer_name, self._button_num
            )

    @callback
    def _handle_double_press(self, value: str) -> None:
        """Handle double press join trigger."""
        if value == "1":
            event_data = {
                "device_name": self._dimmer_name,
                "button": self._button_num,
                "action": "double_press",
            }

            # Fire EventEntity event (updates entity state)
            self._trigger_event("double_press", event_data)

            # Fire event on the bus for automations
            self.hass.bus.async_fire("crestron_button", event_data)

            _LOGGER.debug(
                "%s button %d: double press event", self._dimmer_name, self._button_num
            )

    @callback
    def _handle_hold(self, value: str) -> None:
        """Handle hold join trigger."""
        if value == "1":
            event_data = {
                "device_name": self._dimmer_name,
                "button": self._button_num,
                "action": "hold",
            }

            # Fire EventEntity event (updates entity state)
            self._trigger_event("hold", event_data)

            # Fire event on the bus for automations
            self.hass.bus.async_fire("crestron_button", event_data)

            _LOGGER.debug(
                "%s button %d: hold event", self._dimmer_name, self._button_num
            )
