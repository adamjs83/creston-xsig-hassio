"""Platform for Crestron Binary Sensor integration."""

import voluptuous as vol
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import STATE_ON, STATE_OFF, CONF_NAME, CONF_DEVICE_CLASS
import homeassistant.helpers.config_validation as cv

from .const import HUB, DOMAIN, VERSION, CONF_JOIN, CONF_IS_ON_JOIN, CONF_BINARY_SENSORS

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


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Crestron binary sensors from a config entry."""
    # Get hub reference (could be from entry data or YAML)
    hub_data = hass.data[DOMAIN].get(entry.entry_id)

    if hub_data:
        if isinstance(hub_data, dict):
            hub = hub_data.get(HUB)
        else:
            hub = hub_data
    else:
        hub = hass.data[DOMAIN].get(HUB)

    if not hub:
        _LOGGER.error("No hub found for binary sensors")
        return False

    # Get binary sensors from config entry
    binary_sensors_config = entry.data.get(CONF_BINARY_SENSORS, [])

    if not binary_sensors_config:
        # No UI binary sensors configured
        return True

    entities = []
    for bs_config in binary_sensors_config:
        # Parse string join to integer
        is_on_join_str = bs_config.get(CONF_IS_ON_JOIN)

        if not is_on_join_str or is_on_join_str[0] != 'd':
            _LOGGER.warning("Invalid is_on_join format: %s", is_on_join_str)
            continue

        # Build parsed config with integer join
        parsed_config = {
            CONF_NAME: bs_config.get(CONF_NAME),
            CONF_IS_ON_JOIN: int(is_on_join_str[1:]),  # Parse "d100" -> 100
            CONF_DEVICE_CLASS: bs_config.get(CONF_DEVICE_CLASS),
        }

        # Create entity with from_ui flag
        entities.append(CrestronBinarySensor(hub, parsed_config, from_ui=True))

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d binary sensor(s) from UI config", len(entities))

    return True


class CrestronBinarySensor(BinarySensorEntity, RestoreEntity):
    def __init__(self, hub, config, from_ui=False):
        self._hub = hub
        self._name = config.get(CONF_NAME)
        self._join = config.get(CONF_IS_ON_JOIN)
        self._device_class = config.get(CONF_DEVICE_CLASS)
        self._from_ui = from_ui

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
        if cbtype == "available" or cbtype == f"d{self._join}":
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
            return f"crestron_binary_sensor_ui_d{self._join}"
        return f"crestron_binary_sensor_d{self._join}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"crestron_{self._hub.port}")},
            name="Crestron Control System",
            manufacturer="Crestron Electronics",
            model="XSIG Gateway",
            sw_version=VERSION,
        )

    @property
    def device_class(self):
        return self._device_class

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        if self._hub.has_digital_value(self._join):
            return self._hub.get_digital(self._join)
        return self._restored_is_on