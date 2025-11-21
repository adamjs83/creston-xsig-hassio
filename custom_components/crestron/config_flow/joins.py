"""Join sync handler for Crestron XSIG integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from ..const import (
    CONF_TO_HUB,
    CONF_FROM_HUB,
)

_LOGGER = logging.getLogger(__name__)


class JoinSyncHandler:
    """Handler for join sync (to_joins and from_joins) configuration."""

    def __init__(self, flow):
        """Initialize the join sync handler."""
        self.flow = flow

    async def async_step_add_to_join(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a single to_join with entity picker."""
        errors: dict[str, str] = {}
        is_editing = self.flow._editing_join is not None

        if user_input is not None:
            try:
                join_num = user_input.get("join")
                entity_id = user_input.get("entity_id")
                attribute = user_input.get("attribute", "").strip()
                value_template = user_input.get("value_template", "").strip()

                # Validate join format
                if not join_num or not (join_num[0] in ['d', 'a', 's'] and join_num[1:].isdigit()):
                    errors["join"] = "invalid_join_format"

                # Check for duplicate join (exclude current join if editing)
                current_to_joins = self.flow.config_entry.data.get(CONF_TO_HUB, [])
                old_join_num = self.flow._editing_join.get("join") if is_editing else None
                if join_num != old_join_num and any(j.get("join") == join_num for j in current_to_joins):
                    errors["join"] = "join_already_exists"

                if not errors:
                    # Build new join entry
                    new_join = {"join": join_num}

                    if entity_id:
                        new_join["entity_id"] = entity_id
                    if attribute:
                        new_join["attribute"] = attribute
                    if value_template:
                        new_join["value_template"] = value_template

                    if is_editing:
                        # Replace existing join
                        updated_to_joins = [
                            new_join if j.get("join") == old_join_num else j
                            for j in current_to_joins
                        ]
                        _LOGGER.info("Updated to_join %s for %s", join_num, entity_id)
                    else:
                        # Append new join
                        updated_to_joins = current_to_joins + [new_join]
                        _LOGGER.info("Added to_join %s for %s", join_num, entity_id)

                    # Update config entry
                    new_data = dict(self.flow.config_entry.data)
                    new_data[CONF_TO_HUB] = updated_to_joins

                    self.flow.hass.config_entries.async_update_entry(
                        self.flow.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/editing to_join: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            default_values = {
                "join": self.flow._editing_join.get("join", ""),
                "entity_id": self.flow._editing_join.get("entity_id", ""),
                "attribute": self.flow._editing_join.get("attribute", ""),
                "value_template": self.flow._editing_join.get("value_template", ""),
            }

        # Show form
        add_to_join_schema = vol.Schema(
            {
                vol.Required("join", default=default_values.get("join", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional("entity_id", default=default_values.get("entity_id", "")): selector.EntitySelector(),
                vol.Optional("attribute", default=default_values.get("attribute", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional("value_template", default=default_values.get("value_template", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="add_to_join",
            data_schema=add_to_join_schema,
            errors=errors,
        )

    async def async_step_add_from_join(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a single from_join."""
        errors: dict[str, str] = {}
        is_editing = self.flow._editing_join is not None

        if user_input is not None:
            try:
                join_num = user_input.get("join")
                service = user_input.get("service")
                target_entity = user_input.get("target_entity")

                # Validate join format
                if not join_num or not (join_num[0] in ['d', 'a', 's'] and join_num[1:].isdigit()):
                    errors["join"] = "invalid_join_format"

                # Check for duplicate join (exclude current join if editing)
                current_from_joins = self.flow.config_entry.data.get(CONF_FROM_HUB, [])
                old_join_num = self.flow._editing_join.get("join") if is_editing else None
                if join_num != old_join_num and any(j.get("join") == join_num for j in current_from_joins):
                    errors["join"] = "join_already_exists"

                if not errors:
                    # Build script action
                    script_action = {
                        "service": service,
                    }
                    if target_entity:
                        script_action["target"] = {"entity_id": target_entity}

                    # Build new join entry
                    new_join = {
                        "join": join_num,
                        "script": [script_action]
                    }

                    if is_editing:
                        # Replace existing join
                        updated_from_joins = [
                            new_join if j.get("join") == old_join_num else j
                            for j in current_from_joins
                        ]
                        _LOGGER.info("Updated from_join %s with service %s", join_num, service)
                    else:
                        # Append new join
                        updated_from_joins = current_from_joins + [new_join]
                        _LOGGER.info("Added from_join %s with service %s", join_num, service)

                    # Update config entry
                    new_data = dict(self.flow.config_entry.data)
                    new_data[CONF_FROM_HUB] = updated_from_joins

                    self.flow.hass.config_entries.async_update_entry(
                        self.flow.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    # Clear editing state and return to menu
                    self.flow._editing_join = None
                    return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error adding/editing from_join: %s", err)
                errors["base"] = "unknown"

        # Pre-fill form if editing
        default_values = {}
        if is_editing:
            script_action = self.flow._editing_join.get("script", [{}])[0] if self.flow._editing_join.get("script") else {}
            default_values = {
                "join": self.flow._editing_join.get("join", ""),
                "service": script_action.get("service", ""),
                "target_entity": script_action.get("target", {}).get("entity_id", ""),
            }

        # Show form
        add_from_join_schema = vol.Schema(
            {
                vol.Required("join", default=default_values.get("join", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Required("service", default=default_values.get("service", "")): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional("target_entity", default=default_values.get("target_entity", "")): selector.EntitySelector(),
            }
        )

        return self.flow.async_show_form(
            step_id="add_from_join",
            data_schema=add_from_join_schema,
            errors=errors,
        )

    async def async_step_remove_joins(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove joins by selecting from a list."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                joins_to_remove = user_input.get("joins_to_remove", [])

                if joins_to_remove:
                    current_to_joins = self.flow.config_entry.data.get(CONF_TO_HUB, [])
                    current_from_joins = self.flow.config_entry.data.get(CONF_FROM_HUB, [])

                    # Filter out selected joins
                    updated_to_joins = [j for j in current_to_joins if j.get("join") not in joins_to_remove]
                    updated_from_joins = [j for j in current_from_joins if j.get("join") not in joins_to_remove]

                    # Update config entry
                    new_data = dict(self.flow.config_entry.data)
                    new_data[CONF_TO_HUB] = updated_to_joins
                    new_data[CONF_FROM_HUB] = updated_from_joins

                    self.flow.hass.config_entries.async_update_entry(
                        self.flow.config_entry, data=new_data
                    )

                    # Reload the integration
                    await self.flow._async_reload_integration()

                    _LOGGER.info("Removed %d joins", len(joins_to_remove))

                # Return to menu
                return await self.flow.async_step_init()

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error removing joins: %s", err)
                errors["base"] = "unknown"

        # Build list of all joins for removal selection
        current_to_joins = self.flow.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.flow.config_entry.data.get(CONF_FROM_HUB, [])

        join_options = []
        for j in current_to_joins:
            entity = j.get("entity_id", j.get("value_template", "N/A"))
            join_options.append({
                "label": f"{j.get('join')} → {entity} (to_join)",
                "value": j.get("join")
            })

        for j in current_from_joins:
            script_info = "script" if "script" in j else "N/A"
            join_options.append({
                "label": f"{j.get('join')} → {script_info} (from_join)",
                "value": j.get("join")
            })

        if not join_options:
            # No joins to remove, return to menu
            return await self.flow.async_step_init()

        # Show removal form
        remove_schema = vol.Schema(
            {
                vol.Optional("joins_to_remove"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=join_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=True,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="remove_joins",
            data_schema=remove_schema,
            errors=errors,
        )

    async def async_step_select_join_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which join to edit."""
        if user_input is not None:
            selected_join = user_input.get("join_to_edit")

            if selected_join:
                # Find the join in our data
                current_to_joins = self.flow.config_entry.data.get(CONF_TO_HUB, [])
                current_from_joins = self.flow.config_entry.data.get(CONF_FROM_HUB, [])

                # Check if it's a to_join or from_join
                for join in current_to_joins:
                    if join.get("join") == selected_join:
                        self.flow._editing_join = join
                        return await self.async_step_add_to_join()

                for join in current_from_joins:
                    if join.get("join") == selected_join:
                        self.flow._editing_join = join
                        return await self.async_step_add_from_join()

            # If no join selected, return to menu
            return await self.flow.async_step_init()

        # Build list of all joins for editing
        current_to_joins = self.flow.config_entry.data.get(CONF_TO_HUB, [])
        current_from_joins = self.flow.config_entry.data.get(CONF_FROM_HUB, [])

        join_options = []
        for j in current_to_joins:
            entity = j.get("entity_id", j.get("value_template", "N/A"))
            join_options.append({
                "label": f"{j.get('join')} → {entity} (to_join)",
                "value": j.get("join")
            })

        for j in current_from_joins:
            script_info = "script" if "script" in j else "N/A"
            join_options.append({
                "label": f"{j.get('join')} → {script_info} (from_join)",
                "value": j.get("join")
            })

        if not join_options:
            # No joins to edit, return to menu
            return await self.flow.async_step_init()

        # Show selection form
        select_schema = vol.Schema(
            {
                vol.Required("join_to_edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=join_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="select_join_to_edit",
            data_schema=select_schema,
        )
