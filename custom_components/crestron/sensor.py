"""Platform for Crestron Sensor integration."""

import voluptuous as vol
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import CONF_NAME, CONF_DEVICE_CLASS, CONF_UNIT_OF_MEASUREMENT
import homeassistant.helpers.config_validation as cv

from .const import HUB, DOMAIN, CONF_VALUE_JOIN, CONF_DIVISOR, CONF_SENSORS

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_VALUE_JOIN): cv.positive_int,           
        vol.Required(CONF_DEVICE_CLASS): cv.string,
        vol.Required(CONF_UNIT_OF_MEASUREMENT): cv.string,
        vol.Required(CONF_DIVISOR): int,
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronSensor(hub, config)]
    async_add_entities(entity)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Crestron sensors from a config entry.

    Supports UI-configured sensors (v1.10.0+).
    YAML platform setup (above) handles YAML-configured entities.
    """
    # Get hub from entry data
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if not entry_data:
        _LOGGER.warning("No entry data found for sensor setup")
        return False

    hub_wrapper = entry_data.get('hub_wrapper')
    if not hub_wrapper:
        _LOGGER.warning("No hub_wrapper found for sensor setup")
        return False

    # Get hub from wrapper
    hub = hub_wrapper.hub

    # Load sensors from config entry (UI-configured)
    sensors_config = entry.data.get(CONF_SENSORS, [])

    if sensors_config:
        entities = []
        for sensor_cfg in sensors_config:
            # Parse join string to integer (e.g., "a10" -> 10)
            value_join_str = sensor_cfg.get(CONF_VALUE_JOIN, "")
            if value_join_str and value_join_str[0] == 'a' and value_join_str[1:].isdigit():
                value_join = int(value_join_str[1:])
            else:
                _LOGGER.error(
                    "Invalid value join format for sensor %s: %s",
                    sensor_cfg.get(CONF_NAME), value_join_str
                )
                continue

            # Create config dict with integer join
            config = {
                CONF_NAME: sensor_cfg.get(CONF_NAME),
                CONF_VALUE_JOIN: value_join,
                CONF_DEVICE_CLASS: sensor_cfg.get(CONF_DEVICE_CLASS),
                CONF_UNIT_OF_MEASUREMENT: sensor_cfg.get(CONF_UNIT_OF_MEASUREMENT),
                CONF_DIVISOR: sensor_cfg.get(CONF_DIVISOR, 1),
            }

            entities.append(CrestronSensor(hub, config, from_ui=True))

        if entities:
            async_add_entities(entities)
            _LOGGER.info("Added %d UI-configured sensors", len(entities))

    return True


class CrestronSensor(SensorEntity, RestoreEntity):
    def __init__(self, hub, config, from_ui=False):
        self._hub = hub
        self._name = config.get(CONF_NAME)
        self._join = config.get(CONF_VALUE_JOIN)
        self._device_class = config.get(CONF_DEVICE_CLASS)
        self._unit_of_measurement = config.get(CONF_UNIT_OF_MEASUREMENT)
        self._divisor = config.get(CONF_DIVISOR, 1)
        self._from_ui = from_ui

        # State restoration variable
        self._restored_value = None

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._hub.register_callback(self.process_callback)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in (None, "unknown", "unavailable"):
                try:
                    self._restored_value = float(last_state.state)
                    _LOGGER.debug(
                        f"Restored {self.name}: value={self._restored_value}"
                    )
                except (ValueError, TypeError):
                    pass

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
            return f"crestron_sensor_ui_a{self._join}"
        return f"crestron_sensor_a{self._join}"

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
    def native_value(self):
        """Return the state of the sensor."""
        if self._hub.has_analog_value(self._join):
            return self._hub.get_analog(self._join) / self._divisor
        return self._restored_value

    @property
    def device_class(self):
        return self._device_class

    @property
    def native_unit_of_measurement(self):
        return self._unit_of_measurement
