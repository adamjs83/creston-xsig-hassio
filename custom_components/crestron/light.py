"""Platform for Crestron Light integration."""
from typing import Any

import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    LightEntity,
    ColorMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_TYPE, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import (
    HUB,
    DOMAIN,
    VERSION,
    CONF_BRIGHTNESS_JOIN,
    CONF_LIGHTS,
    CONF_DIMMERS,
    CONF_HAS_LIGHTING_LOAD,
    CONF_LIGHT_BRIGHTNESS_JOIN,
)
from .helpers import get_hub

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_TYPE): cv.string,
        vol.Required(CONF_BRIGHTNESS_JOIN): cv.positive_int,           
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Crestron lights from YAML configuration."""
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronLight(hub, config)]
    async_add_entities(entity)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Crestron lights from a config entry.

    v1.11.0+: Entities can be configured via UI (stored in entry.data[CONF_LIGHTS])
    YAML platform setup (above) still works for backward compatibility.
    """
    hub = get_hub(hass, entry)
    if hub is None:
        _LOGGER.error("No Crestron hub found for light entities")
        return False

    # Get light configurations from config entry
    light_configs = entry.data.get(CONF_LIGHTS, [])
    entities = []

    # Parse join strings to integers and create regular light entities
    for light_config in light_configs:
        # Parse joins from string format ("a30") to integers
        parsed_config = {
            CONF_NAME: light_config.get(CONF_NAME),
            CONF_TYPE: light_config.get(CONF_TYPE, "brightness"),
        }

        # Parse brightness join (required, analog)
        brightness_join_str = light_config.get(CONF_BRIGHTNESS_JOIN)
        if brightness_join_str and brightness_join_str[0] == 'a':
            parsed_config[CONF_BRIGHTNESS_JOIN] = int(brightness_join_str[1:])
        else:
            _LOGGER.warning(
                "Skipping light %s: invalid brightness_join format %s",
                light_config.get(CONF_NAME),
                brightness_join_str
            )
            continue

        entities.append(CrestronLight(hub, parsed_config, from_ui=True))

    # Create light entities from dimmer configs (v1.17.3+)
    dimmers = entry.data.get(CONF_DIMMERS, [])
    for dimmer in dimmers:
        if not dimmer.get(CONF_HAS_LIGHTING_LOAD):
            continue

        dimmer_name = dimmer.get(CONF_NAME)
        brightness_join_str = dimmer.get(CONF_LIGHT_BRIGHTNESS_JOIN)

        if not brightness_join_str:
            continue

        # Parse brightness join
        if brightness_join_str[0] == 'a':
            brightness_join = int(brightness_join_str[1:])
        else:
            _LOGGER.warning(
                "Skipping dimmer light for '%s': invalid brightness_join format %s",
                dimmer_name,
                brightness_join_str
            )
            continue

        # Create light entity for dimmer's lighting load
        light_config = {
            CONF_NAME: "Light",
            CONF_TYPE: "brightness",
            CONF_BRIGHTNESS_JOIN: brightness_join,
        }

        entities.append(
            CrestronLight(
                hub,
                light_config,
                from_ui=True,
                is_dimmer_light=True,
                dimmer_name=dimmer_name
            )
        )

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d light entities from config entry", len(entities))

    return True


class CrestronLight(LightEntity, RestoreEntity):
    """Representation of a Crestron Light."""

    _hub: Any  # CrestronHub type
    _from_ui: bool
    _is_dimmer_light: bool
    _dimmer_name: str | None
    _name: str
    _brightness_join: int
    _restored_state: bool | None
    _restored_brightness: int | None

    def __init__(
        self,
        hub: Any,
        config: dict[str, Any],
        from_ui: bool = False,
        is_dimmer_light: bool = False,
        dimmer_name: str | None = None,
    ) -> None:
        """Initialize the Crestron light."""
        self._hub = hub
        self._from_ui = from_ui  # Track if this is a UI-created entity
        self._is_dimmer_light = is_dimmer_light  # Track if this is a dimmer's lighting load
        self._dimmer_name = dimmer_name  # Parent dimmer name (for device grouping)
        self._name = config.get(CONF_NAME)
        self._brightness_join = config.get(CONF_BRIGHTNESS_JOIN)

        # State restoration variables
        self._restored_state = None
        self._restored_brightness = None

        # Callback reference for proper deregistration
        self._callback_ref = None

        if config.get(CONF_TYPE) == "brightness":
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            # For non-dimmable lights
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

    async def async_added_to_hass(self) -> None:
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._callback_ref = self.process_callback
        self._hub.register_callback(self._callback_ref)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            self._restored_state = last_state.state == STATE_ON
            self._restored_brightness = last_state.attributes.get('brightness')
            _LOGGER.debug(
                f"Restored {self.name}: state={self._restored_state}, "
                f"brightness={self._restored_brightness}"
            )

        # Request current state from Crestron if connected
        if self._hub.is_available():
            self._hub.request_update()
            _LOGGER.debug("Requested update for %s", self.name)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks when entity is removed."""
        if self._callback_ref is not None:
            self._hub.remove_callback(self._callback_ref)

    async def process_callback(self, cbtype: str, value: Any) -> None:
        """Process callback from hub when join value changes."""
        # Only update if this is our join or connection state changed
        if cbtype == "available" or cbtype == f"a{self._brightness_join}":
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._hub.is_available()

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID for this entity."""
        if self._is_dimmer_light:
            return f"crestron_light_dimmer_{self._dimmer_name}_a{self._brightness_join}"
        if self._from_ui:
            return f"crestron_light_ui_a{self._brightness_join}"
        return f"crestron_light_a{self._brightness_join}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this entity."""
        # Dimmer lights group under dimmer device
        if self._is_dimmer_light and self._dimmer_name:
            return DeviceInfo(
                identifiers={(DOMAIN, f"dimmer_{self._dimmer_name}")},
                name=self._dimmer_name,
                manufacturer="Crestron",
                model="Keypad/Dimmer",
            )

        # Regular lights group under main Crestron device
        return DeviceInfo(
            identifiers={(DOMAIN, f"crestron_{self._hub.port}")},
            name="Crestron Control System",
            manufacturer="Crestron Electronics",
            model="XSIG Gateway",
            sw_version=VERSION,
        )

    @property
    def has_entity_name(self) -> bool:
        """Return if entity should use modern naming with device name prefix."""
        return self._is_dimmer_light  # True for dimmer lights (part of dimmer device)

    @property
    def should_poll(self) -> bool:
        """Return if entity should be polled."""
        return False

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light (0-255)."""
        if self._attr_color_mode == ColorMode.BRIGHTNESS:
            # Use real value from Crestron if available (fix: proper scaling from 0-65535 to 0-255)
            if self._hub.has_analog_value(self._brightness_join):
                return int(self._hub.get_analog(self._brightness_join) * 255 / 65535)
            # Use restored brightness if available
            return self._restored_brightness
        return None

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        if self._attr_color_mode == ColorMode.BRIGHTNESS:
            # Use real value from Crestron if available
            if self._hub.has_analog_value(self._brightness_join):
                return int(self._hub.get_analog(self._brightness_join) * 255 / 65535) > 0
            # Use restored state if available, otherwise default to off
            return self._restored_state if self._restored_state is not None else False
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if "brightness" in kwargs:
            # Fix: properly scale from HA brightness (0-255) to Crestron (0-65535)
            brightness = kwargs["brightness"]
            crestron_value = int(brightness * 65535 / 255)
            await self._hub.async_set_analog(self._brightness_join, crestron_value)
        else:
            await self._hub.async_set_analog(self._brightness_join, 65535)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._hub.async_set_analog(self._brightness_join, 0)
