"""Base entity configuration management for Crestron XSIG integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector, entity_registry as er

from ...const import (
    DOMAIN,
    CONF_COVERS,
    CONF_BINARY_SENSORS,
    CONF_SENSORS,
    CONF_LIGHTS,
    CONF_SWITCHES,
    CONF_CLIMATES,
    CONF_MEDIA_PLAYERS,
    CONF_POS_JOIN,
    CONF_IS_ON_JOIN,
    CONF_VALUE_JOIN,
    CONF_BRIGHTNESS_JOIN,
    CONF_SWITCH_JOIN,
    CONF_FLOOR_SP_JOIN,
    CONF_HEAT_SP_JOIN,
    CONF_SOURCE_NUM_JOIN,
)
from homeassistant.const import CONF_NAME, CONF_TYPE

_LOGGER = logging.getLogger(__name__)


class EntityManager:
    """Base class for managing entity configuration across all platforms."""

    def __init__(self, flow):
        """Initialize the entity manager."""
        self.flow = flow

    async def async_step_select_entity_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which entity to edit."""
        if user_input is not None:
            selected_entity = user_input.get("entity_to_edit")

            if selected_entity:
                # Find the entity in our data
                current_covers = self.flow.config_entry.data.get(CONF_COVERS, [])
                current_binary_sensors = self.flow.config_entry.data.get(CONF_BINARY_SENSORS, [])
                current_sensors = self.flow.config_entry.data.get(CONF_SENSORS, [])
                current_lights = self.flow.config_entry.data.get(CONF_LIGHTS, [])
                current_switches = self.flow.config_entry.data.get(CONF_SWITCHES, [])
                current_climates = self.flow.config_entry.data.get(CONF_CLIMATES, [])
                current_media_players = self.flow.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

                # Check if it's a light
                for light in current_lights:
                    if light.get(CONF_NAME) == selected_entity:
                        self.flow._editing_join = light
                        return await self.flow.async_step_add_light()

                # Check if it's a switch
                for switch in current_switches:
                    if switch.get(CONF_NAME) == selected_entity:
                        self.flow._editing_join = switch
                        return await self.flow.async_step_add_switch()

                # Check if it's a cover
                for cover in current_covers:
                    if cover.get(CONF_NAME) == selected_entity:
                        self.flow._editing_join = cover
                        return await self.flow.async_step_add_cover()

                # Check if it's a binary sensor
                for binary_sensor in current_binary_sensors:
                    if binary_sensor.get(CONF_NAME) == selected_entity:
                        self.flow._editing_join = binary_sensor
                        return await self.flow.async_step_add_binary_sensor()

                # Check if it's a sensor
                for sensor in current_sensors:
                    if sensor.get(CONF_NAME) == selected_entity:
                        self.flow._editing_join = sensor
                        return await self.flow.async_step_add_sensor()

                # Check if it's a climate
                for climate in current_climates:
                    if climate.get(CONF_NAME) == selected_entity:
                        self.flow._editing_join = climate
                        # Route to appropriate climate form based on type
                        climate_type = climate.get(CONF_TYPE, "standard")
                        if climate_type == "floor_warming":
                            return await self.flow.async_step_add_climate()
                        else:
                            return await self.flow.async_step_add_climate_standard()

                # Check if it's a media player
                for media_player in current_media_players:
                    if media_player.get(CONF_NAME) == selected_entity:
                        self.flow._editing_join = media_player
                        return await self.flow.async_step_add_media_player()

            # Not found, return to menu
            return await self.flow.async_step_init()

        # Build list of all entities for editing
        current_covers = self.flow.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.flow.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.flow.config_entry.data.get(CONF_SENSORS, [])
        current_lights = self.flow.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.flow.config_entry.data.get(CONF_SWITCHES, [])
        current_climates = self.flow.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.flow.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

        entity_options = []
        for l in current_lights:
            entity_options.append({
                "label": f"{l.get(CONF_NAME)} (Light - {l.get(CONF_BRIGHTNESS_JOIN)})",
                "value": l.get(CONF_NAME)
            })
        for sw in current_switches:
            entity_options.append({
                "label": f"{sw.get(CONF_NAME)} (Switch - {sw.get(CONF_SWITCH_JOIN)})",
                "value": sw.get(CONF_NAME)
            })
        for c in current_covers:
            entity_options.append({
                "label": f"{c.get(CONF_NAME)} (Cover - {c.get(CONF_POS_JOIN)})",
                "value": c.get(CONF_NAME)
            })
        for bs in current_binary_sensors:
            entity_options.append({
                "label": f"{bs.get(CONF_NAME)} (Binary Sensor - {bs.get(CONF_IS_ON_JOIN)})",
                "value": bs.get(CONF_NAME)
            })
        for s in current_sensors:
            entity_options.append({
                "label": f"{s.get(CONF_NAME)} (Sensor - {s.get(CONF_VALUE_JOIN)})",
                "value": s.get(CONF_NAME)
            })
        for cl in current_climates:
            climate_type = cl.get(CONF_TYPE, "standard")
            type_label = "Floor Warming" if climate_type == "floor_warming" else "Standard HVAC"
            join_display = cl.get(CONF_FLOOR_SP_JOIN) if climate_type == "floor_warming" else cl.get(CONF_HEAT_SP_JOIN)
            entity_options.append({
                "label": f"{cl.get(CONF_NAME)} (Climate - {type_label} - {join_display})",
                "value": cl.get(CONF_NAME)
            })
        for mp in current_media_players:
            entity_options.append({
                "label": f"{mp.get(CONF_NAME)} (Media Player - {mp.get(CONF_SOURCE_NUM_JOIN)})",
                "value": mp.get(CONF_NAME)
            })

        if not entity_options:
            # No entities to edit, return to menu
            return await self.flow.async_step_init()

        # Show selection form
        select_schema = vol.Schema(
            {
                vol.Required("entity_to_edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=entity_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="select_entity_to_edit",
            data_schema=select_schema,
        )

    async def async_step_remove_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove entities by selecting from a list."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                entities_to_remove = user_input.get("entities_to_remove", [])

                if entities_to_remove:
                    current_covers = self.flow.config_entry.data.get(CONF_COVERS, [])
                    current_binary_sensors = self.flow.config_entry.data.get(CONF_BINARY_SENSORS, [])
                    current_sensors = self.flow.config_entry.data.get(CONF_SENSORS, [])
                    current_lights = self.flow.config_entry.data.get(CONF_LIGHTS, [])
                    current_switches = self.flow.config_entry.data.get(CONF_SWITCHES, [])
                    current_climates = self.flow.config_entry.data.get(CONF_CLIMATES, [])
                    current_media_players = self.flow.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

                    # Filter out selected entities
                    updated_covers = [c for c in current_covers if c.get(CONF_NAME) not in entities_to_remove]
                    updated_binary_sensors = [bs for bs in current_binary_sensors if bs.get(CONF_NAME) not in entities_to_remove]
                    updated_sensors = [s for s in current_sensors if s.get(CONF_NAME) not in entities_to_remove]
                    updated_lights = [l for l in current_lights if l.get(CONF_NAME) not in entities_to_remove]
                    updated_switches = [sw for sw in current_switches if sw.get(CONF_NAME) not in entities_to_remove]
                    updated_climates = [cl for cl in current_climates if cl.get(CONF_NAME) not in entities_to_remove]
                    updated_media_players = [mp for mp in current_media_players if mp.get(CONF_NAME) not in entities_to_remove]

                    # Update config entry
                    new_data = dict(self.flow.config_entry.data)
                    new_data[CONF_COVERS] = updated_covers
                    new_data[CONF_BINARY_SENSORS] = updated_binary_sensors
                    new_data[CONF_SENSORS] = updated_sensors
                    new_data[CONF_LIGHTS] = updated_lights
                    new_data[CONF_SWITCHES] = updated_switches
                    new_data[CONF_CLIMATES] = updated_climates
                    new_data[CONF_MEDIA_PLAYERS] = updated_media_players

                    self.flow.hass.config_entries.async_update_entry(
                        self.flow.config_entry, data=new_data
                    )

                    # Remove entities from entity registry
                    entity_reg = er.async_get(self.flow.hass)
                    removed_count = 0

                    for entity_name in entities_to_remove:
                        # Find the entity config to get join number
                        entity_config = None
                        entity_type = None

                        # Check if it's a light
                        for light in current_lights:
                            if light.get(CONF_NAME) == entity_name:
                                entity_config = light
                                entity_type = "light"
                                break

                        # Check if it's a switch
                        if not entity_config:
                            for switch in current_switches:
                                if switch.get(CONF_NAME) == entity_name:
                                    entity_config = switch
                                    entity_type = "switch"
                                    break

                        # Check if it's a cover
                        if not entity_config:
                            for cover in current_covers:
                                if cover.get(CONF_NAME) == entity_name:
                                    entity_config = cover
                                    entity_type = "cover"
                                    break

                        # Check if it's a binary sensor
                        if not entity_config:
                            for bs in current_binary_sensors:
                                if bs.get(CONF_NAME) == entity_name:
                                    entity_config = bs
                                    entity_type = "binary_sensor"
                                    break

                        # Check if it's a sensor
                        if not entity_config:
                            for s in current_sensors:
                                if s.get(CONF_NAME) == entity_name:
                                    entity_config = s
                                    entity_type = "sensor"
                                    break

                        # Check if it's a climate
                        if not entity_config:
                            for cl in current_climates:
                                if cl.get(CONF_NAME) == entity_name:
                                    entity_config = cl
                                    entity_type = "climate"
                                    break

                        # Check if it's a media player
                        if not entity_config:
                            for mp in current_media_players:
                                if mp.get(CONF_NAME) == entity_name:
                                    entity_config = mp
                                    entity_type = "media_player"
                                    break

                        if entity_config and entity_type:
                            # Construct unique_id based on entity type
                            if entity_type == "light":
                                brightness_join_str = entity_config.get(CONF_BRIGHTNESS_JOIN, "")
                                if brightness_join_str and brightness_join_str[0] == 'a':
                                    join_num = brightness_join_str[1:]
                                    unique_id = f"crestron_light_ui_a{join_num}"
                                else:
                                    continue
                            elif entity_type == "switch":
                                switch_join_str = entity_config.get(CONF_SWITCH_JOIN, "")
                                if switch_join_str and switch_join_str[0] == 'd':
                                    join_num = switch_join_str[1:]
                                    unique_id = f"crestron_switch_ui_d{join_num}"
                                else:
                                    continue
                            elif entity_type == "cover":
                                pos_join_str = entity_config.get(CONF_POS_JOIN, "")
                                if pos_join_str and pos_join_str[0] == 'a':
                                    join_num = pos_join_str[1:]
                                    unique_id = f"crestron_cover_ui_a{join_num}"
                                else:
                                    continue
                            elif entity_type == "binary_sensor":
                                is_on_join_str = entity_config.get(CONF_IS_ON_JOIN, "")
                                if is_on_join_str and is_on_join_str[0] == 'd':
                                    join_num = is_on_join_str[1:]
                                    unique_id = f"crestron_binary_sensor_ui_d{join_num}"
                                else:
                                    continue
                            elif entity_type == "sensor":
                                value_join_str = entity_config.get(CONF_VALUE_JOIN, "")
                                if value_join_str and value_join_str[0] == 'a':
                                    join_num = value_join_str[1:]
                                    unique_id = f"crestron_sensor_ui_a{join_num}"
                                else:
                                    continue
                            elif entity_type == "climate":
                                # Use setpoint join for floor warming
                                sp_join_str = entity_config.get(CONF_FLOOR_SP_JOIN, "")
                                if sp_join_str and sp_join_str[0] == 'a':
                                    join_num = sp_join_str[1:]
                                    unique_id = f"crestron_climate_ui_a{join_num}"
                                else:
                                    continue
                            elif entity_type == "media_player":
                                source_join_str = entity_config.get(CONF_SOURCE_NUM_JOIN, "")
                                if source_join_str and source_join_str[0] == 'a':
                                    join_num = source_join_str[1:]
                                    unique_id = f"crestron_media_player_ui_a{join_num}"
                                else:
                                    continue

                            # Find and remove entity from registry
                            entity_id = entity_reg.async_get_entity_id(
                                entity_type, DOMAIN, unique_id
                            )

                            if entity_id:
                                entity_reg.async_remove(entity_id)
                                removed_count += 1
                                _LOGGER.info(
                                    "Removed entity %s (unique_id: %s) from registry",
                                    entity_name, unique_id
                                )

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    _LOGGER.info(
                        "Removed %d entities from config, %d from registry",
                        len(entities_to_remove), removed_count
                    )

                # Return to menu
                return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error removing entities: %s", err)
                errors["base"] = "unknown"

        # Build list of all entities for removal selection
        current_covers = self.flow.config_entry.data.get(CONF_COVERS, [])
        current_binary_sensors = self.flow.config_entry.data.get(CONF_BINARY_SENSORS, [])
        current_sensors = self.flow.config_entry.data.get(CONF_SENSORS, [])
        current_lights = self.flow.config_entry.data.get(CONF_LIGHTS, [])
        current_switches = self.flow.config_entry.data.get(CONF_SWITCHES, [])
        current_climates = self.flow.config_entry.data.get(CONF_CLIMATES, [])
        current_media_players = self.flow.config_entry.data.get(CONF_MEDIA_PLAYERS, [])

        entity_options = []
        for l in current_lights:
            entity_options.append({
                "label": f"{l.get(CONF_NAME)} (Light - {l.get(CONF_BRIGHTNESS_JOIN)})",
                "value": l.get(CONF_NAME)
            })
        for sw in current_switches:
            entity_options.append({
                "label": f"{sw.get(CONF_NAME)} (Switch - {sw.get(CONF_SWITCH_JOIN)})",
                "value": sw.get(CONF_NAME)
            })
        for c in current_covers:
            entity_options.append({
                "label": f"{c.get(CONF_NAME)} (Cover - {c.get(CONF_POS_JOIN)})",
                "value": c.get(CONF_NAME)
            })
        for bs in current_binary_sensors:
            entity_options.append({
                "label": f"{bs.get(CONF_NAME)} (Binary Sensor - {bs.get(CONF_IS_ON_JOIN)})",
                "value": bs.get(CONF_NAME)
            })
        for s in current_sensors:
            entity_options.append({
                "label": f"{s.get(CONF_NAME)} (Sensor - {s.get(CONF_VALUE_JOIN)})",
                "value": s.get(CONF_NAME)
            })
        for cl in current_climates:
            climate_type = cl.get(CONF_TYPE, "standard")
            type_label = "Floor Warming" if climate_type == "floor_warming" else "Standard HVAC"
            join_display = cl.get(CONF_FLOOR_SP_JOIN) if climate_type == "floor_warming" else cl.get(CONF_HEAT_SP_JOIN)
            entity_options.append({
                "label": f"{cl.get(CONF_NAME)} (Climate - {type_label} - {join_display})",
                "value": cl.get(CONF_NAME)
            })
        for mp in current_media_players:
            entity_options.append({
                "label": f"{mp.get(CONF_NAME)} (Media Player - {mp.get(CONF_SOURCE_NUM_JOIN)})",
                "value": mp.get(CONF_NAME)
            })

        if not entity_options:
            # No entities to remove, return to menu
            return await self.flow.async_step_init()

        # Show removal form
        remove_schema = vol.Schema(
            {
                vol.Optional("entities_to_remove"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=entity_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=True,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="remove_entities",
            data_schema=remove_schema,
            errors=errors,
        )
