"""Platform for Crestron Binary Sensor integration."""

import voluptuous as vol
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import STATE_ON, STATE_OFF, CONF_NAME, CONF_DEVICE_CLASS
import homeassistant.helpers.config_validation as cv

from .const import HUB, DOMAIN, CONF_JOIN, CONF_IS_ON_JOIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_IS_ON_JOIN): cv.positive_int,           
        vol.Required(CONF_DEVICE_CLASS): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronBinarySensor(hub, config)]
    async_add_entities(entity)


class CrestronBinarySensor(BinarySensorEntity, RestoreEntity):
    def __init__(self, hub, config):
        self._hub = hub
        self._name = config.get(CONF_NAME)
        self._join = config.get(CONF_IS_ON_JOIN)
        self._device_class = config.get(CONF_DEVICE_CLASS)

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
        return f"crestron_binary_sensor_d{self._join}"

    @property
    def device_class(self):
        return self._device_class

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        if self._hub.has_digital_value(self._join):
            return self._hub.get_digital(self._join)
        return self._restored_is_on