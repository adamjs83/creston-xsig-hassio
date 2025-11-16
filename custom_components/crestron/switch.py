"""Platform for Crestron Switch integration."""

import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import STATE_ON, STATE_OFF, CONF_NAME, CONF_DEVICE_CLASS
from .const import HUB, DOMAIN, CONF_SWITCH_JOIN

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

    For v1.6.0, entities are still configured via YAML.
    This stub enables device registry linkage for future entity options flow.
    """
    # No entities added from config entry in v1.6.0
    # YAML platform setup (above) handles entity creation
    return True


class CrestronSwitch(SwitchEntity, RestoreEntity):
    def __init__(self, hub, config):
        self._hub = hub
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
        return self._restored_is_on

    async def async_turn_on(self, **kwargs):
        self._hub.set_digital(self._switch_join, True)

    async def async_turn_off(self, **kwargs):
        self._hub.set_digital(self._switch_join, False)
