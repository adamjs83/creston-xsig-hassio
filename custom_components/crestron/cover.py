"""Platform for Crestron Shades integration."""

import asyncio
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.cover import (
    CoverEntity,
    CoverDeviceClass,
    CoverEntityFeature,
)
from homeassistant.const import CONF_NAME, CONF_TYPE
from .const import (
    HUB,
    DOMAIN,
    CONF_IS_OPENING_JOIN,
    CONF_IS_CLOSING_JOIN,
    CONF_IS_CLOSED_JOIN,
    CONF_STOP_JOIN,
    CONF_POS_JOIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_TYPE): cv.string,
        vol.Required(CONF_POS_JOIN): cv.positive_int,           
        vol.Required(CONF_IS_OPENING_JOIN): cv.positive_int,
        vol.Required(CONF_IS_CLOSING_JOIN): cv.positive_int,
        vol.Required(CONF_IS_CLOSED_JOIN): cv.positive_int,
        vol.Required(CONF_STOP_JOIN): cv.positive_int,
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronShade(hub, config)]
    async_add_entities(entity)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Crestron covers from a config entry.

    For v1.6.0, entities are still configured via YAML.
    This stub enables device registry linkage for future entity options flow.
    """
    # No entities added from config entry in v1.6.0
    # YAML platform setup (above) handles entity creation
    return True


class CrestronShade(CoverEntity, RestoreEntity):
    def __init__(self, hub, config):
        self._hub = hub
        # Initialize with default values
        self._attr_device_class = None
        self._attr_supported_features = 0

        if config.get(CONF_TYPE) == "shade":
            self._attr_device_class = CoverDeviceClass.SHADE
            _LOGGER.debug("Setting device_class to: %s", self._attr_device_class)
            self._attr_supported_features = (
                CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
                CoverEntityFeature.SET_POSITION | CoverEntityFeature.STOP
            )
            _LOGGER.debug("Setting supported_features to: %s", self._attr_supported_features)
        self._should_poll = False

        self._name = config.get(CONF_NAME)
        self._is_opening_join = config.get(CONF_IS_OPENING_JOIN)
        self._is_closing_join = config.get(CONF_IS_CLOSING_JOIN)
        self._is_closed_join = config.get(CONF_IS_CLOSED_JOIN)
        self._stop_join = config.get(CONF_STOP_JOIN)
        self._pos_join = config.get(CONF_POS_JOIN)

        # State restoration variables
        self._restored_position = None
        self._restored_is_closed = None

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._hub.register_callback(self.process_callback)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            self._restored_position = last_state.attributes.get('current_position')
            self._restored_is_closed = last_state.state == 'closed'
            _LOGGER.debug(
                f"Restored {self.name}: position={self._restored_position}, "
                f"closed={self._restored_is_closed}"
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
        return f"crestron_cover_a{self._pos_join}"

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
    def device_class(self):
        return self._attr_device_class

    @property
    def supported_features(self):
        return self._attr_supported_features

    @property
    def should_poll(self):
        return self._should_poll

    @property
    def current_cover_position(self):
        """Return current position of cover."""
        if self._hub.has_analog_value(self._pos_join):
            return self._hub.get_analog(self._pos_join) / 655.35
        return self._restored_position

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        if self._hub.has_digital_value(self._is_opening_join):
            return self._hub.get_digital(self._is_opening_join)
        return None

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        if self._hub.has_digital_value(self._is_closing_join):
            return self._hub.get_digital(self._is_closing_join)
        return None

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self._hub.has_digital_value(self._is_closed_join):
            return self._hub.get_digital(self._is_closed_join)
        return self._restored_is_closed

    async def async_set_cover_position(self, **kwargs):
        self._hub.set_analog(self._pos_join, int(kwargs["position"]) * 655)

    async def async_open_cover(self, **kwargs):
        self._hub.set_analog(self._pos_join, 0xFFFF)

    async def async_close_cover(self, **kwargs):
        self._hub.set_analog(self._pos_join, 0)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover and clear direction state.

        This function does two things:
        1. Sends a stop pulse via the digital stop join
        2. Clears the analog position join to a neutral value

        Clearing the analog join is critical because:
        - async_open_cover() sets it to 0xFFFF (65535)
        - async_close_cover() sets it to 0
        - If we don't clear it, the next same-direction command won't register
          as a change and the Crestron system won't respond

        We use the current position (or mid-point) as the neutral value so the
        cover stays at its stopped position.
        """
        # Send stop pulse
        await self._hub.async_set_digital(self._stop_join, 1)
        await asyncio.sleep(0.2)
        await self._hub.async_set_digital(self._stop_join, 0)

        # Clear the direction state by setting analog to current position
        # This allows immediate direction changes after stopping
        current_pos = self.current_cover_position
        if current_pos is not None:
            # Set to current position (convert percentage back to analog value)
            self._hub.set_analog(self._pos_join, int(current_pos * 655.35))
        else:
            # If we don't have a position, use mid-point (50%)
            self._hub.set_analog(self._pos_join, 32767)
