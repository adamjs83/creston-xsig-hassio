"""Media player entity configuration handler for Crestron XSIG integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from ...const import (
    CONF_MEDIA_PLAYERS,
    CONF_SOURCE_NUM_JOIN,
    CONF_SOURCES,
    CONF_MUTE_JOIN,
    CONF_VOLUME_JOIN,
    CONF_POWER_ON_JOIN,
    CONF_PLAY_JOIN,
    CONF_PAUSE_JOIN,
    CONF_STOP_JOIN,
    CONF_NEXT_JOIN,
    CONF_PREVIOUS_JOIN,
)
from homeassistant.const import CONF_NAME, CONF_DEVICE_CLASS

_LOGGER = logging.getLogger(__name__)


class MediaPlayerEntityHandler:
    """Handler for media player entity configuration."""

    def __init__(self, flow):
        """Initialize the media player entity handler."""
        self.flow = flow

    async def async_step_add_media_player(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a media player entity."""
        errors: dict[str, str] = {}
        is_editing = self.flow._editing_join is not None

        if user_input is not None:
            try:
                name = user_input.get(CONF_NAME)
                device_class = user_input.get(CONF_DEVICE_CLASS, "speaker")
                source_num_join = user_input.get(CONF_SOURCE_NUM_JOIN)
                sources_text = user_input.get(CONF_SOURCES, "")

                # Optional joins
                power_on_join = user_input.get(CONF_POWER_ON_JOIN, "")
                mute_join = user_input.get(CONF_MUTE_JOIN, "")
                volume_join = user_input.get(CONF_VOLUME_JOIN, "")
                play_join = user_input.get(CONF_PLAY_JOIN, "")
                pause_join = user_input.get(CONF_PAUSE_JOIN, "")
                stop_join = user_input.get(CONF_STOP_JOIN, "")
                next_join = user_input.get(CONF_NEXT_JOIN, "")
                previous_join = user_input.get(CONF_PREVIOUS_JOIN, "")

                # Validate source_num_join (required, analog)
                if not source_num_join or not (source_num_join[0] == 'a' and source_num_join[1:].isdigit()):
                    errors[CONF_SOURCE_NUM_JOIN] = "invalid_join_format"

                # Parse and validate sources (required, min 1 source)
                sources_dict = {}
                if sources_text.strip():
                    for line in sources_text.strip().split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        if ':' not in line:
                            errors[CONF_SOURCES] = "invalid_source_format"
                            break
                        try:
                            num_str, name_str = line.split(':', 1)
                            source_num = int(num_str.strip())
                            source_name = name_str.strip()
                            if source_num < 1 or source_num > 99:
                                errors[CONF_SOURCES] = "source_number_out_of_range"
                                break
                            sources_dict[source_num] = source_name
                        except (ValueError, AttributeError):
                            errors[CONF_SOURCES] = "invalid_source_format"
                            break

                if not sources_dict:
                    errors[CONF_SOURCES] = "no_sources_configured"

                # Validate optional joins
                optional_joins = [
                    (CONF_POWER_ON_JOIN, power_on_join, 'd'),
                    (CONF_MUTE_JOIN, mute_join, 'd'),
                    (CONF_VOLUME_JOIN, volume_join, 'a'),
                    (CONF_PLAY_JOIN, play_join, 'd'),
                    (CONF_PAUSE_JOIN, pause_join, 'd'),
                    (CONF_STOP_JOIN, stop_join, 'd'),
                    (CONF_NEXT_JOIN, next_join, 'd'),
                    (CONF_PREVIOUS_JOIN, previous_join, 'd'),
                ]

                for join_field, join_value, join_type in optional_joins:
                    if join_value and not (join_value[0] == join_type and join_value[1:].isdigit()):
                        errors[join_field] = "invalid_join_format"

                # Check for duplicate entity name
                current_media_players = self.flow.config_entry.data.get(CONF_MEDIA_PLAYERS, [])
                old_name = self.flow._editing_join.get(CONF_NAME) if is_editing else None
                if name != old_name and any(mp.get(CONF_NAME) == name for mp in current_media_players):
                    errors[CONF_NAME] = "entity_already_exists"

                if not errors:
                    # Build new media player entry
                    new_media_player = {
                        CONF_NAME: name,
                        CONF_DEVICE_CLASS: device_class,
                        CONF_SOURCE_NUM_JOIN: source_num_join,
                        CONF_SOURCES: sources_dict,
                    }

                    # Add optional joins if provided
                    if power_on_join:
                        new_media_player[CONF_POWER_ON_JOIN] = power_on_join
                    if mute_join:
                        new_media_player[CONF_MUTE_JOIN] = mute_join
                    if volume_join:
                        new_media_player[CONF_VOLUME_JOIN] = volume_join
                    if play_join:
                        new_media_player[CONF_PLAY_JOIN] = play_join
                    if pause_join:
                        new_media_player[CONF_PAUSE_JOIN] = pause_join
                    if stop_join:
                        new_media_player[CONF_STOP_JOIN] = stop_join
                    if next_join:
                        new_media_player[CONF_NEXT_JOIN] = next_join
                    if previous_join:
                        new_media_player[CONF_PREVIOUS_JOIN] = previous_join

                    if is_editing:
                        # Replace existing media player
                        updated_media_players = [
                            new_media_player if mp.get(CONF_NAME) == old_name else mp
                            for mp in current_media_players
                        ]
                        _LOGGER.info("Updated media player %s", name)
                    else:
                        # Append new media player
                        updated_media_players = current_media_players + [new_media_player]
                        _LOGGER.info("Added media player %s", name)

                    # Update config entry
                    new_data = dict(self.flow.config_entry.data)
                    new_data[CONF_MEDIA_PLAYERS] = updated_media_players

                    self.flow.hass.config_entries.async_update_entry(
                        self.flow.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/updating media player: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            # Convert sources dict to text format
            sources_dict = self.flow._editing_join.get(CONF_SOURCES, {})
            sources_text = '\n'.join(f"{num}: {name}" for num, name in sorted(sources_dict.items()))

            default_values = {
                CONF_NAME: self.flow._editing_join.get(CONF_NAME, ""),
                CONF_DEVICE_CLASS: self.flow._editing_join.get(CONF_DEVICE_CLASS, "speaker"),
                CONF_SOURCE_NUM_JOIN: self.flow._editing_join.get(CONF_SOURCE_NUM_JOIN, ""),
                CONF_SOURCES: sources_text,
                CONF_POWER_ON_JOIN: self.flow._editing_join.get(CONF_POWER_ON_JOIN, ""),
                CONF_MUTE_JOIN: self.flow._editing_join.get(CONF_MUTE_JOIN, ""),
                CONF_VOLUME_JOIN: self.flow._editing_join.get(CONF_VOLUME_JOIN, ""),
                CONF_PLAY_JOIN: self.flow._editing_join.get(CONF_PLAY_JOIN, ""),
                CONF_PAUSE_JOIN: self.flow._editing_join.get(CONF_PAUSE_JOIN, ""),
                CONF_STOP_JOIN: self.flow._editing_join.get(CONF_STOP_JOIN, ""),
                CONF_NEXT_JOIN: self.flow._editing_join.get(CONF_NEXT_JOIN, ""),
                CONF_PREVIOUS_JOIN: self.flow._editing_join.get(CONF_PREVIOUS_JOIN, ""),
            }

        # Show form
        add_media_player_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=default_values.get(CONF_NAME, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_DEVICE_CLASS, default=default_values.get(CONF_DEVICE_CLASS, "speaker")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "TV", "value": "tv"},
                            {"label": "Speaker", "value": "speaker"},
                            {"label": "Receiver", "value": "receiver"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_SOURCE_NUM_JOIN, default=default_values.get(CONF_SOURCE_NUM_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_SOURCES, default=default_values.get(CONF_SOURCES, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                        multiline=True,
                    )
                ),
                vol.Optional(CONF_POWER_ON_JOIN, default=default_values.get(CONF_POWER_ON_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_MUTE_JOIN, default=default_values.get(CONF_MUTE_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_VOLUME_JOIN, default=default_values.get(CONF_VOLUME_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_PLAY_JOIN, default=default_values.get(CONF_PLAY_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_PAUSE_JOIN, default=default_values.get(CONF_PAUSE_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_STOP_JOIN, default=default_values.get(CONF_STOP_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_NEXT_JOIN, default=default_values.get(CONF_NEXT_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_PREVIOUS_JOIN, default=default_values.get(CONF_PREVIOUS_JOIN, "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_media_player",
            data_schema=add_media_player_schema,
            errors=errors,
            description_placeholders={
                "sources_help": "Enter one source per line in format: number: name\nExample:\n1: HDMI 1\n2: HDMI 2\n3: Chromecast"
            },
        )
