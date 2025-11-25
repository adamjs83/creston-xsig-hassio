"""Platform for Crestron Media Player integration."""

import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from homeassistant.const import (
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)

from .const import (
    HUB,
    DOMAIN,
    VERSION,
    CONF_MUTE_JOIN,
    CONF_VOLUME_JOIN,
    CONF_SOURCE_NUM_JOIN,
    CONF_SOURCES,
    CONF_MEDIA_PLAYERS,
    CONF_POWER_ON_JOIN,
    CONF_POWER_OFF_JOIN,
    CONF_PLAY_JOIN,
    CONF_PAUSE_JOIN,
    CONF_STOP_JOIN,
    CONF_NEXT_JOIN,
    CONF_PREVIOUS_JOIN,
    CONF_REPEAT_JOIN,
    CONF_SHUFFLE_JOIN,
)
from homeassistant.const import CONF_DEVICE_CLASS

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_MUTE_JOIN): cv.positive_int,
        vol.Optional(CONF_VOLUME_JOIN): cv.positive_int,
        vol.Optional(CONF_SOURCE_NUM_JOIN): cv.positive_int,
        vol.Optional(CONF_SOURCES): {cv.positive_int: cv.string},
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronRoom(hub, config)]
    async_add_entities(entity)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Crestron media players from a config entry (v1.19.0+)."""
    hub = hass.data[DOMAIN].get(HUB) or hass.data[DOMAIN].get(entry.entry_id, {}).get(HUB)
    if not hub:
        _LOGGER.error("Hub not found for media player setup")
        return False

    media_players = entry.data.get(CONF_MEDIA_PLAYERS, [])
    if not media_players:
        _LOGGER.debug("No UI media players configured")
        return True

    entities = []
    for mp_config in media_players:
        # Parse join numbers (convert "a1" to 1, "d1" to 1, etc.)
        parsed_config = dict(mp_config)

        # Parse source_num_join (required, analog)
        source_num_join_str = mp_config.get(CONF_SOURCE_NUM_JOIN, "")
        if source_num_join_str and source_num_join_str[0] == 'a':
            parsed_config[CONF_SOURCE_NUM_JOIN] = int(source_num_join_str[1:])

        # Parse optional joins
        join_mappings = [
            (CONF_POWER_ON_JOIN, 'd'),
            (CONF_MUTE_JOIN, 'd'),
            (CONF_VOLUME_JOIN, 'a'),
            (CONF_PLAY_JOIN, 'd'),
            (CONF_PAUSE_JOIN, 'd'),
            (CONF_STOP_JOIN, 'd'),
            (CONF_NEXT_JOIN, 'd'),
            (CONF_PREVIOUS_JOIN, 'd'),
            (CONF_REPEAT_JOIN, 'd'),
            (CONF_SHUFFLE_JOIN, 'd'),
        ]

        for join_key, expected_type in join_mappings:
            join_str = mp_config.get(join_key, "")
            if join_str and join_str[0] == expected_type:
                parsed_config[join_key] = int(join_str[1:])
            elif join_key in parsed_config:
                # Remove if invalid or empty
                parsed_config.pop(join_key, None)

        # Create entity with from_ui flag
        entity = CrestronRoom(hub, parsed_config, from_ui=True)
        entities.append(entity)

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Set up %d UI media player(s)", len(entities))

    return True


class CrestronRoom(MediaPlayerEntity, RestoreEntity):
    def __init__(self, hub, config, from_ui=False):
        self._hub = hub
        self._name = config.get(CONF_NAME, "Unnamed Device")
        self._device_class = config.get(CONF_DEVICE_CLASS, "speaker")
        self._from_ui = from_ui

        # Join configuration
        self._source_number_join = config.get(CONF_SOURCE_NUM_JOIN)
        self._sources = config.get(CONF_SOURCES, {})
        self._mute_join = config.get(CONF_MUTE_JOIN)
        self._volume_join = config.get(CONF_VOLUME_JOIN)
        self._power_on_join = config.get(CONF_POWER_ON_JOIN)
        self._power_off_join = config.get(CONF_POWER_OFF_JOIN)
        self._play_join = config.get(CONF_PLAY_JOIN)
        self._pause_join = config.get(CONF_PAUSE_JOIN)
        self._stop_join = config.get(CONF_STOP_JOIN)
        self._next_join = config.get(CONF_NEXT_JOIN)
        self._previous_join = config.get(CONF_PREVIOUS_JOIN)
        self._repeat_join = config.get(CONF_REPEAT_JOIN)
        self._shuffle_join = config.get(CONF_SHUFFLE_JOIN)

        # Calculate supported features based on available joins
        self._attr_supported_features = self._calculate_supported_features()

        # State restoration variables
        self._restored_state = None
        self._restored_source = None
        self._restored_volume = None
        self._restored_is_muted = None

    def _calculate_supported_features(self):
        """Calculate supported features based on configured joins."""
        features = 0

        # Source selection (required)
        if self._source_number_join and self._sources:
            features |= MediaPlayerEntityFeature.SELECT_SOURCE
            features |= MediaPlayerEntityFeature.TURN_OFF  # source=0 turns off

        # Power control
        if self._power_on_join:
            features |= MediaPlayerEntityFeature.TURN_ON

        # Volume control
        if self._mute_join:
            features |= MediaPlayerEntityFeature.VOLUME_MUTE
        if self._volume_join:
            features |= MediaPlayerEntityFeature.VOLUME_SET

        # Transport controls
        if self._play_join:
            features |= MediaPlayerEntityFeature.PLAY
        if self._pause_join:
            features |= MediaPlayerEntityFeature.PAUSE
        if self._stop_join:
            features |= MediaPlayerEntityFeature.STOP
        if self._next_join:
            features |= MediaPlayerEntityFeature.NEXT_TRACK
        if self._previous_join:
            features |= MediaPlayerEntityFeature.PREVIOUS_TRACK

        return features

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._hub.register_callback(self.process_callback)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            self._restored_state = last_state.state
            self._restored_source = last_state.attributes.get('source')
            self._restored_volume = last_state.attributes.get('volume_level')
            self._restored_is_muted = last_state.attributes.get('is_volume_muted')
            _LOGGER.debug(
                f"Restored {self.name}: state={self._restored_state}, "
                f"source={self._restored_source}, volume={self._restored_volume}"
            )

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype, value):
        # Only update if this is one of our joins or connection state changed
        if cbtype == "available":
            self.async_write_ha_state()
            return

        # Build set of relevant joins (handle None values for optional joins)
        relevant_joins = set()
        if self._source_number_join:
            relevant_joins.add(f"a{self._source_number_join}")
        if self._mute_join:
            relevant_joins.add(f"d{self._mute_join}")
        if self._volume_join:
            relevant_joins.add(f"a{self._volume_join}")
        if self._power_on_join:
            relevant_joins.add(f"d{self._power_on_join}")
        if self._power_off_join:
            relevant_joins.add(f"d{self._power_off_join}")

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
            return f"crestron_media_player_ui_a{self._source_number_join}"
        return f"crestron_media_player_a{self._source_number_join}"

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
    def should_poll(self):
        return False

    @property
    def device_class(self):
        return self._device_class

    @property
    def supported_features(self):
        return self._attr_supported_features

    @property
    def source_list(self):
        if self._sources is None:
            return []
        return list(self._sources.values())

    @property
    def source(self):
        """Return the current input source."""
        if not self._source_number_join or not self._sources:
            return None
        if self._hub.has_analog_value(self._source_number_join):
            source_num = self._hub.get_analog(self._source_number_join)
            if source_num == 0 or source_num not in self._sources:
                return None
            return self._sources[source_num]
        return self._restored_source

    @property
    def state(self):
        """Return the state of the media player."""
        if self._hub.has_analog_value(self._source_number_join):
            if self._hub.get_analog(self._source_number_join) == 0:
                return STATE_OFF
            else:
                return STATE_ON
        return self._restored_state

    @property
    def is_volume_muted(self):
        """Return if volume is muted."""
        if self._hub.has_digital_value(self._mute_join):
            return self._hub.get_digital(self._mute_join)
        return self._restored_is_muted

    @property
    def volume_level(self):
        """Return the volume level (0-1)."""
        if self._hub.has_analog_value(self._volume_join):
            return self._hub.get_analog(self._volume_join) / 65535
        return self._restored_volume

    async def async_mute_volume(self, mute):
        self._hub.set_digital(self._mute_join, mute)

    async def async_set_volume_level(self, volume):
        await self._hub.async_set_analog(self._volume_join, int(volume * 65535))

    async def async_select_source(self, source):
        for input_num, name in self._sources.items():
            if name == source:
                await self._hub.async_set_analog(self._source_number_join, input_num)

    async def async_turn_off(self):
        """Turn off the media player by setting source to 0."""
        if self._power_off_join:
            self._hub.set_digital(self._power_off_join, True)
        else:
            # Fallback: set source to 0
            await self._hub.async_set_analog(self._source_number_join, 0)

    async def async_turn_on(self):
        """Turn on the media player."""
        if self._power_on_join:
            self._hub.set_digital(self._power_on_join, True)

    async def async_media_play(self):
        """Send play command."""
        if self._play_join:
            self._hub.set_digital(self._play_join, True)

    async def async_media_pause(self):
        """Send pause command."""
        if self._pause_join:
            self._hub.set_digital(self._pause_join, True)

    async def async_media_stop(self):
        """Send stop command."""
        if self._stop_join:
            self._hub.set_digital(self._stop_join, True)

    async def async_media_next_track(self):
        """Send next track command."""
        if self._next_join:
            self._hub.set_digital(self._next_join, True)

    async def async_media_previous_track(self):
        """Send previous track command."""
        if self._previous_join:
            self._hub.set_digital(self._previous_join, True)
