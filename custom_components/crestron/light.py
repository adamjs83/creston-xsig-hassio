"""Platform for Crestron Light integration."""
import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    LightEntity,
    LightEntityFeature,
    ColorMode,
)
from homeassistant.const import CONF_NAME, CONF_TYPE, STATE_ON
from homeassistant.helpers.restore_state import RestoreEntity
from .const import HUB, DOMAIN, CONF_BRIGHTNESS_JOIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_TYPE): cv.string,
        vol.Required(CONF_BRIGHTNESS_JOIN): cv.positive_int,           
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronLight(hub, config)]
    async_add_entities(entity)


class CrestronLight(LightEntity, RestoreEntity):
    def __init__(self, hub, config):
        self._hub = hub
        self._name = config.get(CONF_NAME)
        self._brightness_join = config.get(CONF_BRIGHTNESS_JOIN)

        # State restoration variables
        self._restored_state = None
        self._restored_brightness = None

        if config.get(CONF_TYPE) == "brightness":
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            # For non-dimmable lights
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._hub.register_callback(self.process_callback)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            self._restored_state = last_state.state == STATE_ON
            self._restored_brightness = last_state.attributes.get('brightness')
            _LOGGER.debug(
                f"Restored {self.name}: state={self._restored_state}, "
                f"brightness={self._restored_brightness}"
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
        return f"crestron_light_a{self._brightness_join}"

    @property
    def should_poll(self):
        return False

    @property
    def brightness(self):
        """Return the brightness of the light (0-255)."""
        if self._attr_color_mode == ColorMode.BRIGHTNESS:
            # Use real value from Crestron if available (fix: proper scaling from 0-65535 to 0-255)
            if self._hub.has_analog_value(self._brightness_join):
                return int(self._hub.get_analog(self._brightness_join) * 255 / 65535)
            # Use restored brightness if available
            return self._restored_brightness
        return None

    @property
    def is_on(self):
        """Return true if light is on."""
        if self._attr_color_mode == ColorMode.BRIGHTNESS:
            # Use real value from Crestron if available
            if self._hub.has_analog_value(self._brightness_join):
                return int(self._hub.get_analog(self._brightness_join) * 255 / 65535) > 0
            # Use restored state if available
            return self._restored_state if self._restored_state is not None else None
        return False

    async def async_turn_on(self, **kwargs):
        """Turn on the light."""
        if "brightness" in kwargs:
            # Fix: properly scale from HA brightness (0-255) to Crestron (0-65535)
            brightness = kwargs["brightness"]
            crestron_value = int(brightness * 65535 / 255)
            self._hub.set_analog(self._brightness_join, crestron_value)
        else:
            self._hub.set_analog(self._brightness_join, 65535)

    async def async_turn_off(self, **kwargs):
        """Turn off the light."""
        self._hub.set_analog(self._brightness_join, 0)
