"""Platform for Crestron Switch integration."""

import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import STATE_ON, STATE_OFF, CONF_NAME, CONF_DEVICE_CLASS
from .const import HUB, DOMAIN, CONF_SWITCH_JOIN, CONF_SWITCHES

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

    if not switch_configs:
        _LOGGER.debug("No switch entities configured in config entry")
        return True

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

    return True


class CrestronSwitch(SwitchEntity, RestoreEntity):
    def __init__(self, hub, config, from_ui=False):
        self._hub = hub
        self._from_ui = from_ui  # Track if this is a UI-created entity
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
                f"Restored {self.name}: is_on={self._restored_is_on}"
            )

        # Request current state from Crestron if connected
        if self._hub.is_available():
            self._hub.request_update()
            _LOGGER.debug(f"Requested update for {self.name}")

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype, value):
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
        if self._from_ui:
            return f"crestron_switch_ui_d{self._switch_join}"
        return f"crestron_switch_d{self._switch_join}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"crestron_{self._hub.port}")},
            name="Crestron Control System",
            manufacturer="Crestron Electronics",
            model="XSIG Gateway",
            sw_version="1.6.0",
        )

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
