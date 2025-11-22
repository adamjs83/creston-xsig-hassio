"""LED Binding Manager for Crestron Integration."""
import logging
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_LED_BINDINGS,
    CONF_DIMMERS,
    BINDABLE_DOMAINS,
    STATE_TO_LED,
)

_LOGGER = logging.getLogger(__name__)


class LEDBindingManager:
    """Manages LED bindings for Crestron dimmer/keypad buttons."""

    def __init__(self, hass: HomeAssistant, hub, config_entry: ConfigEntry):
        """Initialize the LED binding manager."""
        self.hass = hass
        self._hub = hub
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id  # Store entry ID for fresh lookups
        self._bindings: dict[str, dict[str, Any]] = {}
        self._listeners: dict[str, Callable] = {}

    async def async_setup(self) -> None:
        """Set up LED bindings from config entry options."""
        self._load_bindings()
        await self._register_all_listeners()
        _LOGGER.info("LED binding manager initialized with %d bindings", len(self._bindings))

    def _load_bindings(self) -> None:
        """Load LED bindings from config entry data."""
        # Always get fresh entry to ensure we have latest data
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if not entry:
            _LOGGER.warning("Config entry not found during binding load")
            return

        led_bindings = entry.data.get(CONF_LED_BINDINGS, {})
        dimmers = entry.data.get(CONF_DIMMERS, [])

        self._bindings = {}

        for dimmer in dimmers:
            dimmer_name = dimmer.get("name")
            dimmer_bindings = led_bindings.get(dimmer_name, {})

            for button_num_str, binding_config in dimmer_bindings.items():
                if binding_config and "entity_id" in binding_config:
                    # Construct LED entity ID
                    led_entity_id = f"switch.{dimmer_name}_led_{button_num_str}".lower().replace(" ", "_")

                    self._bindings[led_entity_id] = {
                        "entity_id": binding_config["entity_id"],
                        "invert": binding_config.get("invert", False),
                        "dimmer_name": dimmer_name,
                        "button_num": int(button_num_str),
                    }

    async def _register_all_listeners(self) -> None:
        """Register state change listeners for all bindings."""
        for led_entity_id, binding in self._bindings.items():
            await self._register_listener(led_entity_id, binding)

    async def _register_listener(self, led_entity_id: str, binding: dict) -> None:
        """Register a state change listener for a binding."""
        bound_entity_id = binding["entity_id"]

        # Remove old listener if exists
        if led_entity_id in self._listeners:
            self._listeners[led_entity_id]()
            del self._listeners[led_entity_id]

        # Create and register new listener
        @callback
        async def state_change_handler(event: Event) -> None:
            await self._sync_led_state(led_entity_id, binding)

        self._listeners[led_entity_id] = async_track_state_change_event(
            self.hass,
            [bound_entity_id],
            state_change_handler
        )

        _LOGGER.debug(
            "Registered listener: %s → %s (invert=%s)",
            bound_entity_id,
            led_entity_id,
            binding.get("invert"),
        )

        # Sync initial state
        await self._sync_led_state(led_entity_id, binding)

    async def _sync_led_state(self, led_entity_id: str, binding: dict) -> None:
        """Sync LED state based on bound entity state."""
        bound_entity_id = binding["entity_id"]
        invert = binding.get("invert", False)

        # Get bound entity state
        state = self.hass.states.get(bound_entity_id)
        if not state:
            _LOGGER.debug("Bound entity %s not found", bound_entity_id)
            return

        # Map state to LED on/off
        should_be_on = STATE_TO_LED.get(state.state, False)
        if invert:
            should_be_on = not should_be_on

        # Call switch service to update LED
        service = "turn_on" if should_be_on else "turn_off"

        _LOGGER.debug(
            "LED sync: %s (%s) → %s (%s) [invert=%s]",
            bound_entity_id,
            state.state,
            led_entity_id,
            "ON" if should_be_on else "OFF",
            invert,
        )

        await self.hass.services.async_call(
            "switch",
            service,
            {"entity_id": led_entity_id},
            blocking=False,
        )

    async def async_reload(self) -> None:
        """Reload bindings from config entry options."""
        # Remove all listeners
        for remove_listener in self._listeners.values():
            remove_listener()
        self._listeners.clear()

        # Reload bindings
        self._load_bindings()
        await self._register_all_listeners()

        _LOGGER.info("LED bindings reloaded: %d active bindings", len(self._bindings))

    async def async_unload(self) -> None:
        """Remove all listeners."""
        for remove_listener in self._listeners.values():
            remove_listener()
        self._listeners.clear()
        _LOGGER.info("LED binding manager unloaded")
