"""LED Binding configuration handler."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from ..const import BINDABLE_DOMAINS, CONF_DIMMERS, CONF_LED_BINDINGS, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class LEDBindingHandler:
    """Handler for LED binding configuration."""

    flow: Any  # Type of OptionsFlowHandler to avoid circular import

    def __init__(self, options_flow: Any) -> None:
        """Initialize the LED binding handler."""
        self.flow = options_flow

    async def async_step_led_binding_menu(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show LED binding management menu."""
        dimmers: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_DIMMERS, [])

        if not dimmers:
            return self.flow.async_abort(reason="no_dimmers_configured")

        if user_input is not None:
            dimmer_name: str | None = user_input.get("dimmer_to_configure")

            # Store selected dimmer for next step
            self.flow._selected_dimmer = dimmer_name
            return await self.async_step_configure_dimmer_leds()

        # Build dimmer selection
        dimmer_options: list[dict[str, str]] = [
            {"label": f"{d.get('name')} ({d.get('button_count')} buttons)", "value": d.get("name")} for d in dimmers
        ]

        schema: vol.Schema = vol.Schema(
            {
                vol.Required("dimmer_to_configure"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=dimmer_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.flow.async_show_form(
            step_id="led_binding_menu",
            data_schema=schema,
        )

    async def async_step_configure_dimmer_leds(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Configure LED bindings for selected dimmer."""
        dimmer_name: str = self.flow._selected_dimmer

        # Find dimmer config
        dimmers: list[dict[str, Any]] = self.flow.config_entry.data.get(CONF_DIMMERS, [])
        dimmer: dict[str, Any] | None = next((d for d in dimmers if d.get("name") == dimmer_name), None)

        if not dimmer:
            return self.flow.async_abort(reason="dimmer_not_found")

        button_count: int = dimmer.get("button_count", 2)

        if user_input is not None:
            # Save bindings
            bindings: dict[str, dict[str, Any] | None] = {}

            for btn_num in range(1, button_count + 1):
                entity_id: str | None = user_input.get(f"button_{btn_num}_entity")
                invert: bool = user_input.get(f"button_{btn_num}_invert", False)

                if entity_id:
                    bindings[str(btn_num)] = {
                        "entity_id": entity_id,
                        "invert": invert,
                    }
                else:
                    bindings[str(btn_num)] = None

            # Save to config entry data (consistent with other entity handlers)
            # Get fresh entry to ensure we're updating the latest version
            fresh_entry: ConfigEntry | None = self.flow.hass.config_entries.async_get_entry(
                self.flow.config_entry.entry_id
            )
            if not fresh_entry:
                _LOGGER.error("Config entry not found, cannot save LED bindings")
                return self.flow.async_abort(reason="entry_not_found")

            new_data: dict[str, Any] = dict(fresh_entry.data)
            led_bindings: dict[str, dict[str, dict[str, Any] | None]] = new_data.get(CONF_LED_BINDINGS, {})
            led_bindings[dimmer_name] = bindings
            new_data[CONF_LED_BINDINGS] = led_bindings

            self.flow.hass.config_entries.async_update_entry(fresh_entry, data=new_data)

            _LOGGER.info(
                "Updated LED bindings for dimmer '%s': %d buttons configured",
                dimmer_name,
                sum(1 for b in bindings.values() if b is not None),
            )

            # Reload LED binding manager
            await self._reload_led_binding_manager()

            # Clear temp state
            del self.flow._selected_dimmer

            return self.flow.async_create_entry(title="", data={})

        # Build dynamic form
        schema_fields: dict[vol.Marker, Any] = {}

        # Get existing bindings from fresh entry data (not options)
        fresh_entry: ConfigEntry | None = self.flow.hass.config_entries.async_get_entry(self.flow.config_entry.entry_id)
        existing_bindings: dict[str, dict[str, Any] | None] = {}
        if fresh_entry:
            existing_bindings = fresh_entry.data.get(CONF_LED_BINDINGS, {}).get(dimmer_name, {})

        for btn_num in range(1, button_count + 1):
            # Handle None values for unbound buttons
            existing: dict[str, Any] = existing_bindings.get(str(btn_num)) or {}

            # Entity selector (domain-filtered)
            # Only set default if there's an actual entity_id (avoid "Entity None" error)
            existing_entity: str | None = existing.get("entity_id") if existing else None
            if existing_entity:
                schema_fields[vol.Optional(f"button_{btn_num}_entity", default=existing_entity)] = (
                    selector.EntitySelector(selector.EntitySelectorConfig(domain=list(BINDABLE_DOMAINS.keys())))
                )
            else:
                # No default - field starts blank and can be left blank
                schema_fields[vol.Optional(f"button_{btn_num}_entity")] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=list(BINDABLE_DOMAINS.keys()))
                )

            # Invert checkbox
            schema_fields[vol.Optional(f"button_{btn_num}_invert", default=existing.get("invert", False))] = (
                selector.BooleanSelector()
            )

        schema: vol.Schema = vol.Schema(schema_fields)

        return self.flow.async_show_form(
            step_id="configure_dimmer_leds",
            data_schema=schema,
            description_placeholders={
                "dimmer_name": dimmer_name,
                "button_count": str(button_count),
            },
        )

    async def _reload_led_binding_manager(self) -> None:
        """Reload the LED binding manager."""
        entry_data: dict[str, Any] | None = self.flow.hass.data[DOMAIN].get(self.flow.config_entry.entry_id)

        if entry_data and "led_binding_manager" in entry_data:
            led_manager: Any = entry_data["led_binding_manager"]
            await led_manager.async_reload()
