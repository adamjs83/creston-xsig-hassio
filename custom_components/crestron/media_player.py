"""Platform for Crestron Media Player integration."""

import logging
from typing import Any

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_CLASS, CONF_NAME, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import voluptuous as vol

from .const import (
    CONF_MEDIA_PLAYERS,
    CONF_MUTE_JOIN,
    CONF_NEXT_JOIN,
    CONF_PAUSE_JOIN,
    CONF_PLAY_JOIN,
    CONF_POWER_OFF_JOIN,
    CONF_POWER_ON_JOIN,
    CONF_PREVIOUS_JOIN,
    CONF_REPEAT_JOIN,
    CONF_SHUFFLE_JOIN,
    CONF_SOURCE_NUM_JOIN,
    CONF_SOURCES,
    CONF_STOP_JOIN,
    CONF_VOLUME_JOIN,
    DOMAIN,
    HUB,
    VERSION,
)
from .helpers import get_hub

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


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronRoom(hub, config)]
    async_add_entities(entity)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Crestron media players from a config entry (v1.19.0+)."""
    hub = get_hub(hass, entry)
    if hub is None:
        _LOGGER.error("No Crestron hub found for media player entities")
        return False

    media_players: list[dict[str, Any]] = entry.data.get(CONF_MEDIA_PLAYERS, [])
    if not media_players:
        _LOGGER.debug("No UI media players configured")
        return True

    entities: list[CrestronRoom] = []
    for mp_config in media_players:
        # Parse join numbers (convert "a1" to 1, "d1" to 1, etc.)
        parsed_config = dict(mp_config)

        # Parse source_num_join (required, analog)
        source_num_join_str = mp_config.get(CONF_SOURCE_NUM_JOIN, "")
        if source_num_join_str and source_num_join_str[0] == "a":
            parsed_config[CONF_SOURCE_NUM_JOIN] = int(source_num_join_str[1:])

        # Parse optional joins
        join_mappings = [
            (CONF_POWER_ON_JOIN, "d"),
            (CONF_MUTE_JOIN, "d"),
            (CONF_VOLUME_JOIN, "a"),
            (CONF_PLAY_JOIN, "d"),
            (CONF_PAUSE_JOIN, "d"),
            (CONF_STOP_JOIN, "d"),
            (CONF_NEXT_JOIN, "d"),
            (CONF_PREVIOUS_JOIN, "d"),
            (CONF_REPEAT_JOIN, "d"),
            (CONF_SHUFFLE_JOIN, "d"),
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
    def __init__(self, hub: Any, config: dict[str, Any], from_ui: bool = False) -> None:
        self._hub: Any = hub
        self._name: str = config.get(CONF_NAME, "Unnamed Device")
        self._device_class: str = config.get(CONF_DEVICE_CLASS, "speaker")
        self._from_ui: bool = from_ui

        # Join configuration
        self._source_number_join: int | None = config.get(CONF_SOURCE_NUM_JOIN)
        self._sources: dict[int, str] = config.get(CONF_SOURCES, {})
        self._mute_join: int | None = config.get(CONF_MUTE_JOIN)
        self._volume_join: int | None = config.get(CONF_VOLUME_JOIN)
        self._power_on_join: int | None = config.get(CONF_POWER_ON_JOIN)
        self._power_off_join: int | None = config.get(CONF_POWER_OFF_JOIN)
        self._play_join: int | None = config.get(CONF_PLAY_JOIN)
        self._pause_join: int | None = config.get(CONF_PAUSE_JOIN)
        self._stop_join: int | None = config.get(CONF_STOP_JOIN)
        self._next_join: int | None = config.get(CONF_NEXT_JOIN)
        self._previous_join: int | None = config.get(CONF_PREVIOUS_JOIN)
        self._repeat_join: int | None = config.get(CONF_REPEAT_JOIN)
        self._shuffle_join: int | None = config.get(CONF_SHUFFLE_JOIN)

        # Calculate supported features based on available joins
        self._attr_supported_features: MediaPlayerEntityFeature = self._calculate_supported_features()

        # State restoration variables
        self._restored_state: str | None = None
        self._restored_source: str | None = None
        self._restored_volume: float | None = None
        self._restored_is_muted: bool | None = None

        # Callback reference for proper deregistration
        self._callback_ref = None

    def _calculate_supported_features(self) -> MediaPlayerEntityFeature:
        """Calculate supported features based on configured joins."""
        features: int = 0

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

    async def async_added_to_hass(self) -> None:
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._callback_ref = self.process_callback
        self._hub.register_callback(self._callback_ref)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            self._restored_state = last_state.state
            self._restored_source = last_state.attributes.get("source")
            self._restored_volume = last_state.attributes.get("volume_level")
            self._restored_is_muted = last_state.attributes.get("is_volume_muted")
            _LOGGER.debug(
                f"Restored {self.name}: state={self._restored_state}, "
                f"source={self._restored_source}, volume={self._restored_volume}"
            )

    async def async_will_remove_from_hass(self) -> None:
        if self._callback_ref is not None:
            self._hub.remove_callback(self._callback_ref)

    async def process_callback(self, cbtype: str, value: Any) -> None:
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
    def available(self) -> bool:
        return self._hub.is_available()

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
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
    def should_poll(self) -> bool:
        return False

    @property
    def device_class(self) -> str:
        return self._device_class

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        return self._attr_supported_features

    @property
    def source_list(self) -> list[str]:
        if self._sources is None:
            return []
        return list(self._sources.values())

    @property
    def source(self) -> str | None:
        """Return the current input source."""
        if not self._source_number_join or not self._sources:
            return None
        if self._hub.has_analog_value(self._source_number_join):
            source_num: int = self._hub.get_analog(self._source_number_join)
            if source_num == 0 or source_num not in self._sources:
                return None
            return self._sources[source_num]
        return self._restored_source

    @property
    def state(self) -> str | None:
        """Return the state of the media player."""
        if self._hub.has_analog_value(self._source_number_join):
            if self._hub.get_analog(self._source_number_join) == 0:
                return STATE_OFF
            return STATE_ON
        return self._restored_state

    @property
    def is_volume_muted(self) -> bool | None:
        """Return if volume is muted."""
        if self._hub.has_digital_value(self._mute_join):
            return self._hub.get_digital(self._mute_join)
        return self._restored_is_muted

    @property
    def volume_level(self) -> float | None:
        """Return the volume level (0-1)."""
        if self._hub.has_analog_value(self._volume_join):
            return self._hub.get_analog(self._volume_join) / 65535
        return self._restored_volume

    async def async_mute_volume(self, mute: bool) -> None:
        self._hub.set_digital(self._mute_join, mute)

    async def async_set_volume_level(self, volume: float) -> None:
        await self._hub.async_set_analog(self._volume_join, int(volume * 65535))

    async def async_select_source(self, source: str) -> None:
        for input_num, name in self._sources.items():
            if name == source:
                await self._hub.async_set_analog(self._source_number_join, input_num)

    async def async_turn_off(self) -> None:
        """Turn off the media player by setting source to 0."""
        if self._power_off_join:
            self._hub.set_digital(self._power_off_join, True)
        else:
            # Fallback: set source to 0
            await self._hub.async_set_analog(self._source_number_join, 0)

    async def async_turn_on(self) -> None:
        """Turn on the media player."""
        if self._power_on_join:
            self._hub.set_digital(self._power_on_join, True)

    async def async_media_play(self) -> None:
        """Send play command."""
        if self._play_join:
            self._hub.set_digital(self._play_join, True)

    async def async_media_pause(self) -> None:
        """Send pause command."""
        if self._pause_join:
            self._hub.set_digital(self._pause_join, True)

    async def async_media_stop(self) -> None:
        """Send stop command."""
        if self._stop_join:
            self._hub.set_digital(self._stop_join, True)

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        if self._next_join:
            self._hub.set_digital(self._next_join, True)

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        if self._previous_join:
            self._hub.set_digital(self._previous_join, True)
