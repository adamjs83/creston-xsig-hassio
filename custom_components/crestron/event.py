"""Support for Crestron button press events."""

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_BASE_JOIN, CONF_BUTTON_COUNT, CONF_DIMMERS, DOMAIN
from .helpers import get_hub

_LOGGER = logging.getLogger(__name__)

# Event types that button entities can fire
EVENT_TYPES: list[str] = ["press", "double_press", "hold"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crestron button event entities from a config entry."""
    hub = get_hub(hass, config_entry)
    if hub is None:
        _LOGGER.error("No Crestron hub found for event entities")
        return

    dimmers: list[dict[str, Any]] = config_entry.data.get(CONF_DIMMERS, [])

    if not dimmers:
        return

    entities: list[CrestronButtonEvent] = []
    for dimmer in dimmers:
        dimmer_name: str = dimmer.get(CONF_NAME, "Unknown")
        base_join: str | None = dimmer.get(CONF_BASE_JOIN)
        # Note: JSON serialization converts int keys to strings
        manual_joins: dict[str, dict[str, str]] | None = dimmer.get("manual_joins")
        button_count: int = dimmer.get(CONF_BUTTON_COUNT, 2)

        mode: str = "manual" if manual_joins else "auto-sequential"
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
            btn_key: str = str(button_num)
            if manual_joins and btn_key in manual_joins:
                # Manual mode: use explicitly configured joins
                press_join: str = manual_joins[btn_key]["press"]
                double_join: str = manual_joins[btn_key]["double"]
                hold_join: str = manual_joins[btn_key]["hold"]
            else:
                # Auto-sequential mode: calculate from base join
                # Button 1: d10 (press), d11 (double), d12 (hold)
                # Button 2: d13 (press), d14 (double), d15 (hold)
                base_offset: int = (button_num - 1) * 3
                press_join_num: int = int(base_join[1:]) + base_offset
                press_join = f"d{press_join_num}"
                double_join = f"d{press_join_num + 1}"
                hold_join = f"d{press_join_num + 2}"

            entity: CrestronButtonEvent = CrestronButtonEvent(
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

    _attr_event_types: list[str] = EVENT_TYPES
    _attr_device_class: EventDeviceClass = EventDeviceClass.BUTTON
    _attr_has_entity_name: bool = True

    _hub: Any
    _dimmer_name: str
    _button_num: int
    _press_join: str
    _double_join: str
    _hold_join: str
    _name: str
    _callback_ref: Callable[[str, str], Any] | None

    def __init__(
        self,
        hub: Any,
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

        # Callback reference for proper deregistration
        self._callback_ref = None

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
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
        self._callback_ref = self.process_callback
        self._hub.register_callback(self._callback_ref)

        _LOGGER.debug(
            "Registered button %d event listeners: %s (press), %s (double), %s (hold)",
            self._button_num,
            self._press_join,
            self._double_join,
            self._hold_join,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks when entity is removed."""
        if self._callback_ref is not None:
            self._hub.remove_callback(self._callback_ref)

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
            event_data: dict[str, str | int] = {
                "device_name": self._dimmer_name,
                "button": self._button_num,
                "action": "press",
            }

            # Fire EventEntity event (updates entity state)
            self._trigger_event("press", event_data)

            # Fire event on the bus for automations
            self.hass.bus.async_fire("crestron_button", event_data)

            _LOGGER.debug("%s button %d: press event", self._dimmer_name, self._button_num)

    @callback
    def _handle_double_press(self, value: str) -> None:
        """Handle double press join trigger."""
        if value == "1":
            event_data: dict[str, str | int] = {
                "device_name": self._dimmer_name,
                "button": self._button_num,
                "action": "double_press",
            }

            # Fire EventEntity event (updates entity state)
            self._trigger_event("double_press", event_data)

            # Fire event on the bus for automations
            self.hass.bus.async_fire("crestron_button", event_data)

            _LOGGER.debug("%s button %d: double press event", self._dimmer_name, self._button_num)

    @callback
    def _handle_hold(self, value: str) -> None:
        """Handle hold join trigger."""
        if value == "1":
            event_data: dict[str, str | int] = {
                "device_name": self._dimmer_name,
                "button": self._button_num,
                "action": "hold",
            }

            # Fire EventEntity event (updates entity state)
            self._trigger_event("hold", event_data)

            # Fire event on the bus for automations
            self.hass.bus.async_fire("crestron_button", event_data)

            _LOGGER.debug("%s button %d: hold event", self._dimmer_name, self._button_num)
