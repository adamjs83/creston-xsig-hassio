"""Platform for Crestron Switch integration."""

import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import STATE_ON, STATE_OFF, CONF_NAME, CONF_DEVICE_CLASS
from .const import (
    HUB,
    DOMAIN,
    CONF_SWITCH_JOIN,
    CONF_SWITCHES,
    CONF_DIMMERS,
    CONF_BASE_JOIN,
    CONF_BUTTON_COUNT,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): cv.string,
        vol.Required(CONF_SWITCH_JOIN): cv.positive_int,           
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronSwitch(hub, config)]
    async_add_entities(entity)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Crestron switches from a config entry.

    v1.12.0+: Entities can be configured via UI (stored in entry.data[CONF_SWITCHES])
    YAML platform setup (above) still works for backward compatibility.
    """
    # Get the hub - try entry-specific first, fall back to HUB key
    hub_data = hass.data[DOMAIN].get(entry.entry_id)

    if hub_data:
        # Hub data is stored as dict with HUB key
        if isinstance(hub_data, dict):
            hub = hub_data.get(HUB)
        else:
            hub = hub_data  # Fallback for direct hub reference
    else:
        # Fallback to global HUB key
        hub = hass.data[DOMAIN].get(HUB)

    if hub is None:
        _LOGGER.error("No Crestron hub found for switch entities")
        return False

    # Get switch configurations from config entry
    switch_configs = entry.data.get(CONF_SWITCHES, [])

    # Parse join strings to integers and create entities
    entities = []
    for switch_config in switch_configs:
        # Parse joins from string format ("d30") to integers
        parsed_config = {
            CONF_NAME: switch_config.get(CONF_NAME),
            CONF_DEVICE_CLASS: switch_config.get(CONF_DEVICE_CLASS, "switch"),
        }

        # Parse switch join (required, digital)
        switch_join_str = switch_config.get(CONF_SWITCH_JOIN)
        if switch_join_str and switch_join_str[0] == 'd':
            parsed_config[CONF_SWITCH_JOIN] = int(switch_join_str[1:])
        else:
            _LOGGER.warning(
                "Skipping switch %s: invalid switch_join format %s",
                switch_config.get(CONF_NAME),
                switch_join_str
            )
            continue

        entities.append(CrestronSwitch(hub, parsed_config, from_ui=True))

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d switch entities from config entry", len(entities))

    # v1.17.0+: Create LED switches from dimmer/keypad configurations
    dimmers = entry.data.get(CONF_DIMMERS, [])
    led_entities = []

    for dimmer in dimmers:
        dimmer_name = dimmer.get(CONF_NAME, "Unknown")
        base_join = dimmer.get(CONF_BASE_JOIN)
        manual_joins = dimmer.get("manual_joins")
        button_count = dimmer.get(CONF_BUTTON_COUNT, 2)

        mode = "manual" if manual_joins else "auto-sequential"
        _LOGGER.debug(
            "Creating LED switch entities for dimmer '%s' (%s mode, %d buttons)",
            dimmer_name,
            mode,
            button_count,
        )

        # Create LED switches (1 per button)
        # Uses the press join for OUTPUT (bidirectional join usage)
        for button_num in range(1, button_count + 1):
            # Get press join for this button (manual or auto-sequential)
            if manual_joins and button_num in manual_joins:
                # Manual mode: use explicitly configured press join
                press_join_str = manual_joins[button_num]["press"]
                press_join = int(press_join_str[1:])
            else:
                # Auto-sequential mode: calculate from base join
                base_offset = (button_num - 1) * 3
                press_join = int(base_join[1:]) + base_offset

            led_config = {
                CONF_NAME: f"LED {button_num}",
                CONF_SWITCH_JOIN: press_join,
                CONF_DEVICE_CLASS: "switch",
            }

            led_entity = CrestronSwitch(hub, led_config, from_ui=True, is_led=True, dimmer_name=dimmer_name)
            led_entities.append(led_entity)

    if led_entities:
        async_add_entities(led_entities)
        _LOGGER.info("Added %d LED switch entities from dimmers", len(led_entities))

    return True


class CrestronSwitch(SwitchEntity, RestoreEntity):
    def __init__(self, hub, config, from_ui=False, is_led=False, dimmer_name=None):
        self._hub = hub
        self._from_ui = from_ui  # Track if this is a UI-created entity
        self._is_led = is_led  # Track if this is an LED switch
        self._dimmer_name = dimmer_name  # Parent dimmer name (for device grouping)
        self._name = config.get(CONF_NAME)
        self._switch_join = config.get(CONF_SWITCH_JOIN)
        self._device_class = config.get(CONF_DEVICE_CLASS, "switch")

        # State restoration variable
        self._restored_is_on = None

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._hub.register_callback(self.process_callback)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            self._restored_is_on = last_state.state == STATE_ON
            _LOGGER.debug(
                "Restored %s: is_on=%s", self.name, self._restored_is_on
            )

        # Request current state from Crestron if connected
        if self._hub.is_available():
            self._hub.request_update()
            _LOGGER.debug("Requested update for %s", self.name)

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype, value):
        # Only update if this is our join or connection state changed
        if cbtype == "available" or cbtype == f"d{self._switch_join}":
            self.async_write_ha_state()

    @property
    def available(self):
        return self._hub.is_available()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """Return unique ID for this entity."""
        if self._is_led:
            return f"crestron_led_{self._dimmer_name}_d{self._switch_join}"
        if self._from_ui:
            return f"crestron_switch_ui_d{self._switch_join}"
        return f"crestron_switch_d{self._switch_join}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this entity."""
        # LED switches group under dimmer device
        if self._is_led and self._dimmer_name:
            return DeviceInfo(
                identifiers={(DOMAIN, f"dimmer_{self._dimmer_name}")},
                name=self._dimmer_name,
                manufacturer="Crestron",
                model="Keypad/Dimmer",
            )

        # Regular switches group under main Crestron device
        return DeviceInfo(
            identifiers={(DOMAIN, f"crestron_{self._hub.port}")},
            name="Crestron Control System",
            manufacturer="Crestron Electronics",
            model="XSIG Gateway",
            sw_version="1.6.0",
        )

    @property
    def has_entity_name(self):
        """Return if entity should use modern naming with device name prefix."""
        return self._is_led  # True for LED switches (part of dimmer device)

    @property
    def should_poll(self):
        return False

    @property
    def device_class(self):
        return self._device_class

    @property
    def is_on(self):
        """Return true if switch is on."""
        if self._hub.has_digital_value(self._switch_join):
            return self._hub.get_digital(self._switch_join)
        # Use restored state if available, otherwise default to off
        return self._restored_is_on if self._restored_is_on is not None else False

    async def async_turn_on(self, **kwargs):
        self._hub.set_digital(self._switch_join, True)

    async def async_turn_off(self, **kwargs):
        self._hub.set_digital(self._switch_join, False)
