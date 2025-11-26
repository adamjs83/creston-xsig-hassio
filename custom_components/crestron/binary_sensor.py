"""Platform for Crestron Binary Sensor integration."""

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_CLASS, CONF_NAME, STATE_ON
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import voluptuous as vol

from .const import CONF_BINARY_SENSORS, CONF_IS_ON_JOIN, DOMAIN, HUB, VERSION
from .helpers import get_hub

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_IS_ON_JOIN): cv.positive_int,
        vol.Required(CONF_DEVICE_CLASS): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Crestron binary sensors from YAML configuration."""
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronBinarySensor(hub, config)]
    async_add_entities(entity)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Crestron binary sensors from a config entry."""
    hub = get_hub(hass, entry)
    if hub is None:
        _LOGGER.error("No Crestron hub found for binary sensor entities")
        return False

    # Get binary sensors from config entry
    binary_sensors_config: list[dict[str, Any]] = entry.data.get(CONF_BINARY_SENSORS, [])

    if not binary_sensors_config:
        # No UI binary sensors configured
        return True

    entities: list[CrestronBinarySensor] = []
    for bs_config in binary_sensors_config:
        # Parse string join to integer
        is_on_join_str: str | None = bs_config.get(CONF_IS_ON_JOIN)

        if not is_on_join_str or is_on_join_str[0] != "d":
            _LOGGER.warning("Invalid is_on_join format: %s", is_on_join_str)
            continue

        # Build parsed config with integer join
        parsed_config: dict[str, Any] = {
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
    """Representation of a Crestron Binary Sensor."""

    def __init__(self, hub: Any, config: dict[str, Any], from_ui: bool = False) -> None:
        """Initialize the binary sensor."""
        self._hub: Any = hub
        self._name: str | None = config.get(CONF_NAME)
        self._join: int | None = config.get(CONF_IS_ON_JOIN)
        self._device_class: str | None = config.get(CONF_DEVICE_CLASS)
        self._from_ui: bool = from_ui

        # State restoration variable
        self._restored_is_on: bool | None = None

        # Callback reference for proper deregistration
        self._callback_ref = None

    async def async_added_to_hass(self) -> None:
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._callback_ref = self.process_callback
        self._hub.register_callback(self._callback_ref)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            self._restored_is_on = last_state.state == STATE_ON
            _LOGGER.debug("Restored %s: is_on=%s", self.name, self._restored_is_on)

        # Request current state from Crestron if connected
        if self._hub.is_available():
            self._hub.request_update()
            _LOGGER.debug("Requested update for %s", self.name)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks when entity is removed."""
        if self._callback_ref is not None:
            self._hub.remove_callback(self._callback_ref)

    async def process_callback(self, cbtype: str, value: Any) -> None:
        """Process callbacks from the hub."""
        # Only update if this is our join or connection state changed
        if cbtype == "available" or cbtype == f"d{self._join}":
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._hub.is_available()

    @property
    def name(self) -> str | None:
        """Return the name of the binary sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
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
    def device_class(self) -> str | None:
        """Return the device class of the binary sensor."""
        return self._device_class

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self._hub.has_digital_value(self._join):
            return self._hub.get_digital(self._join)
        return self._restored_is_on
