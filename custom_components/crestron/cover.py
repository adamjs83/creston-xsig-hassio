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
    CONF_COVERS,
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

    v1.8.0+: Entities can be configured via UI (stored in entry.data[CONF_COVERS])
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
        _LOGGER.error("No Crestron hub found for cover entities")
        return False

    # Get cover configurations from config entry
    cover_configs = entry.data.get(CONF_COVERS, [])

    if not cover_configs:
        _LOGGER.debug("No cover entities configured in config entry")
        return True

    # Parse join strings to integers and create entities
    entities = []
    for cover_config in cover_configs:
        # Parse joins from string format ("a30", "d31") to integers
        parsed_config = {
            CONF_NAME: cover_config.get(CONF_NAME),
            CONF_TYPE: cover_config.get(CONF_TYPE, "shade"),
        }

        # Parse position join (required, analog)
        pos_join_str = cover_config.get(CONF_POS_JOIN)
        if pos_join_str and pos_join_str[0] == 'a':
            parsed_config[CONF_POS_JOIN] = int(pos_join_str[1:])
        else:
            _LOGGER.warning(
                "Skipping cover %s: invalid pos_join format %s",
                cover_config.get(CONF_NAME),
                pos_join_str
            )
            continue

        # Parse optional digital joins
        for join_key in [CONF_IS_OPENING_JOIN, CONF_IS_CLOSING_JOIN,
                        CONF_IS_CLOSED_JOIN, CONF_STOP_JOIN]:
            join_str = cover_config.get(join_key)
            if join_str and join_str[0] == 'd':
                parsed_config[join_key] = int(join_str[1:])

        entities.append(CrestronShade(hub, parsed_config, from_ui=True))

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d cover entities from config entry", len(entities))

    return True


class CrestronShade(CoverEntity, RestoreEntity):
    def __init__(self, hub, config, from_ui=False):
        self._hub = hub
        self._from_ui = from_ui  # Track if this is a UI-created entity
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

        # Request current state from Crestron if connected
        if self._hub.is_available():
            self._hub.request_update()
            _LOGGER.debug(f"Requested update for {self.name}")

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype, value):
        # Only update if this is one of our joins or connection state changed
        if cbtype == "available":
            self.async_write_ha_state()
            return

        # Build set of relevant joins (handle None values for optional joins)
        relevant_joins = {f"a{self._pos_join}"}
        if self._is_opening_join:
            relevant_joins.add(f"d{self._is_opening_join}")
        if self._is_closing_join:
            relevant_joins.add(f"d{self._is_closing_join}")
        if self._is_closed_join:
            relevant_joins.add(f"d{self._is_closed_join}")
        if self._stop_join:
            relevant_joins.add(f"d{self._stop_join}")

        if cbtype in relevant_joins:
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
            return f"crestron_cover_ui_a{self._pos_join}"
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
        # If we have closed state feedback, use it
        if self._hub.has_digital_value(self._is_closed_join):
            return self._hub.get_digital(self._is_closed_join)

        # Otherwise, infer from position when not moving
        # (opening/closing state takes precedence)
        if not self.is_opening and not self.is_closing:
            position = self.current_cover_position
            if position is not None:
                # Closed if position is at or very close to 0
                return position < 1

        # Fallback to restored state if available
        return self._restored_is_closed

    async def async_set_cover_position(self, **kwargs):
        await self._hub.async_set_analog(self._pos_join, int(kwargs["position"]) * 655)

    async def async_open_cover(self, **kwargs):
        await self._hub.async_set_analog(self._pos_join, 0xFFFF)

    async def async_close_cover(self, **kwargs):
        await self._hub.async_set_analog(self._pos_join, 0)

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
            await self._hub.async_set_analog(self._pos_join, int(current_pos * 655.35))
        else:
            # If we don't have a position, use mid-point (50%)
            await self._hub.async_set_analog(self._pos_join, 32767)
