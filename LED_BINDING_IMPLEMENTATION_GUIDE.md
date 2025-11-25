# LED Binding & Button Actions Implementation Guide

## Problem Statement

The Crestron integration has dimmer/keypad devices with:
- **6 buttons** per dimmer (each fires: press, double_press, hold events)
- **6 LED switches** per dimmer (need visual feedback binding to other entities)

### Previous Failed Approaches

1. **Select Entities (v1.17.0 - v1.20.7)**
   - Created `select.dimmer_button_X_led_binding` entities
   - Options: ALL bindable entities in Home Assistant (300+)
   - **Problem**: Entity registry update events exceeded 32KB database limit
   - Caused massive database performance issues

2. **Blueprint with Optional Entity Triggers (v1.20.9 - v1.21.0)**
   - Blueprint with optional entity triggers for buttons and LED bindings
   - **Problem**: Home Assistant blueprints don't support optional triggers
   - Error: "Entity IDs cannot be None" when optional fields left empty
   - Template variables in triggers don't work

3. **Blueprint with Device Triggers**
   - Tried device automation triggers
   - **Problem**: Crestron integration doesn't support device triggers
   - Error: "Integration 'crestron' does not support device automation triggers"

### Home Assistant Constraints

- Blueprints can't have optional entity triggers
- Entity registry updates have 32KB limit
- Select entities with 300+ options cause database issues
- Template variables don't work in blueprint triggers
- Device triggers not available for custom integrations without automation platform

---

## 10/10 Solution: Domain-Filtered Options Flow with LED Binding Manager

### Core Innovation

**Recognize that LED binding is configuration, not entity state.**

Store LED bindings in **config entry options (JSON)** instead of creating select entities (entity registry). This:
- Avoids 32KB database limit
- Provides superior user experience
- Uses Home Assistant's built-in config entry patterns
- Enables domain-filtered entity selectors

### Why This Achieves 10/10

| Criteria | Score | Reason |
|----------|-------|--------|
| **User Experience** | 10/10 | Domain-filtered selectors (15-50 entities vs 300+), searchable, single-page config, familiar UI |
| **Performance** | 10/10 | Zero entity registry bloat, O(1) lookups, direct callbacks, no database overhead |
| **Maintainability** | 10/10 | Clean separation via LEDBindingManager class, follows HA patterns, easy to test |
| **Flexibility** | 10/10 | Supports all bindable domains, handles edge cases, invert logic, multiple dimmers |
| **HA Compatibility** | 10/10 | Uses standard config entry options, domain filtering (built-in), no hacks |

### Architecture Overview

```
User configures binding via Options Flow
    ↓
Saves to config_entry.options["led_bindings"]
    ↓
LEDBindingManager.async_setup() loads bindings
    ↓
For each binding, registers async_track_state_change_event
    ↓
Bound entity state changes (e.g., light.dining_room turns on)
    ↓
State listener callback fires
    ↓
_sync_led_state() is called
    ├→ Maps state to LED on/off (using STATE_TO_LED)
    ├→ Applies invert flag if set
    └→ Calls switch.turn_on or switch.turn_off service
        ↓
LED switch updates
    ↓
Hub sends digital join to Crestron
    ↓
Physical LED updates
```

---

## File Structure

### Files to Create

```
custom_components/crestron/
├── led_binding_manager.py           # NEW: Core LED binding manager (~150 lines)
└── config_flow/
    └── led_bindings.py              # NEW: LED binding options flow handler (~100 lines)
```

### Files to Modify

```
custom_components/crestron/
├── __init__.py                      # Update: Register LED binding manager
├── const.py                         # Update: Add LED binding constants
├── select.py                        # Update: Keep deprecation notice
├── switch.py                        # No changes needed
└── config_flow/
    ├── __init__.py                  # Update: Import LED binding handler
    ├── flow.py                      # Update: Add LED binding menu option
    └── menus.py                     # Update: Add LED binding menu item
```

---

## Data Storage Format

### Config Entry Options Structure

```json
{
  "led_bindings": {
    "Kitchen Keypad": {
      "1": {
        "entity_id": "light.dining_room",
        "invert": false
      },
      "2": {
        "entity_id": "switch.porch_light",
        "invert": false
      },
      "3": {
        "entity_id": "cover.garage_door",
        "invert": true
      },
      "4": null
    },
    "Living Room Dimmer": {
      "1": {
        "entity_id": "light.living_room",
        "invert": false
      },
      "2": null,
      "3": null,
      "4": null,
      "5": null,
      "6": null
    }
  }
}
```

**Key points:**
- Stored in `config_entry.options` (not `data`)
- Nested by dimmer name, then button number
- Button numbers are strings (JSON keys must be strings)
- `null` means no binding (button LED not bound)
- `invert` flag for reverse logic (LED on when entity is off)

---

## User Interface Flow

### Step 1: Navigate to LED Bindings

```
Settings → Devices & Services → Crestron → Configure
├── Add Entity
├── Manage Dimmers/Keypads
└── Configure LED Bindings  ← Click here
```

### Step 2: Select Dimmer

```
┌─────────────────────────────────────────┐
│ Select Dimmer to Configure              │
│ ┌─────────────────────────────────────┐ │
│ │ Kitchen Keypad (4 buttons)      ▼   │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Other options:                          │
│ - Living Room Dimmer (6 buttons)        │
│ - Master Bedroom (2 buttons)            │
└─────────────────────────────────────────┘
```

### Step 3: Configure LED Bindings

```
┌──────────────────────────────────────────────────────┐
│ Configure LED Bindings: Kitchen Keypad (4 buttons)   │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Button 1 LED                                         │
│ ┌──────────────────────────────────────────────┐    │
│ │ 🔍 Search or select entity...            ▼   │    │ ← SEARCHABLE DROPDOWN
│ └──────────────────────────────────────────────┘    │
│ □ Invert (LED on when entity is off)                │
│                                                      │
│ Button 2 LED                                         │
│ ┌──────────────────────────────────────────────┐    │
│ │ Switch: Porch Light                      ▼   │    │
│ └──────────────────────────────────────────────┘    │
│ ☑ Invert (LED on when entity is off)                │
│                                                      │
│ Button 3 LED                                         │
│ ┌──────────────────────────────────────────────┐    │
│ │ 🔍 Search or select entity...            ▼   │    │
│ └──────────────────────────────────────────────┘    │
│ □ Invert (LED on when entity is off)                │
│                                                      │
│          [Cancel]              [Submit]              │
└──────────────────────────────────────────────────────┘
```

**Entity Selector Dropdown (domain-filtered):**
```
┌─────────────────────────────────────────┐
│ 🔍 Search entities...                   │ ← Type to filter
├─────────────────────────────────────────┤
│ 💡 Lights                               │
│   Kitchen Light                         │
│   Dining Room                           │
├─────────────────────────────────────────┤
│ 🔌 Switches                             │
│   Porch Light                           │
│   Coffee Maker                          │
├─────────────────────────────────────────┤
│ 🚪 Covers                               │
│   Garage Door                           │
├─────────────────────────────────────────┤
│ ... (only ~15-50 relevant entities)     │
└─────────────────────────────────────────┘
```

---

## Implementation Details

### 1. LED Binding Manager (`led_binding_manager.py`)

**Purpose:** Central manager for LED bindings, handles state listeners and LED sync

```python
"""LED Binding Manager for Crestron Integration."""
import logging
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_LED_BINDINGS,
    CONF_DIMMERS,
    BINDABLE_DOMAINS,
    STATE_TO_LED,
)

_LOGGER = logging.getLogger(__name__)


class LEDBindingManager:
    """Manages LED bindings for Crestron dimmer/keypad buttons."""

    def __init__(self, hass: HomeAssistant, hub, config_entry: ConfigEntry):
        """Initialize the LED binding manager."""
        self.hass = hass
        self._hub = hub
        self._config_entry = config_entry
        self._bindings: dict[str, dict[str, Any]] = {}
        self._listeners: dict[str, Callable] = {}

    async def async_setup(self) -> None:
        """Set up LED bindings from config entry options."""
        self._load_bindings()
        await self._register_all_listeners()
        _LOGGER.info("LED binding manager initialized with %d bindings", len(self._bindings))

    def _load_bindings(self) -> None:
        """Load LED bindings from config entry options."""
        led_bindings = self._config_entry.options.get(CONF_LED_BINDINGS, {})
        dimmers = self._config_entry.data.get(CONF_DIMMERS, [])

        self._bindings = {}

        for dimmer in dimmers:
            dimmer_name = dimmer.get("name")
            dimmer_bindings = led_bindings.get(dimmer_name, {})

            for button_num_str, binding_config in dimmer_bindings.items():
                if binding_config and "entity_id" in binding_config:
                    # Construct LED entity ID
                    led_entity_id = f"switch.{dimmer_name}_led_{button_num_str}".lower().replace(" ", "_")

                    self._bindings[led_entity_id] = {
                        "entity_id": binding_config["entity_id"],
                        "invert": binding_config.get("invert", False),
                        "dimmer_name": dimmer_name,
                        "button_num": int(button_num_str),
                    }

    async def _register_all_listeners(self) -> None:
        """Register state change listeners for all bindings."""
        for led_entity_id, binding in self._bindings.items():
            await self._register_listener(led_entity_id, binding)

    async def _register_listener(self, led_entity_id: str, binding: dict) -> None:
        """Register a state change listener for a binding."""
        bound_entity_id = binding["entity_id"]

        # Remove old listener if exists
        if led_entity_id in self._listeners:
            self._listeners[led_entity_id]()
            del self._listeners[led_entity_id]

        # Create and register new listener
        @callback
        async def state_change_handler(event: Event) -> None:
            await self._sync_led_state(led_entity_id, binding)

        self._listeners[led_entity_id] = async_track_state_change_event(
            self.hass,
            [bound_entity_id],
            state_change_handler
        )

        _LOGGER.debug(
            "Registered listener: %s → %s (invert=%s)",
            bound_entity_id,
            led_entity_id,
            binding.get("invert"),
        )

        # Sync initial state
        await self._sync_led_state(led_entity_id, binding)

    async def _sync_led_state(self, led_entity_id: str, binding: dict) -> None:
        """Sync LED state based on bound entity state."""
        bound_entity_id = binding["entity_id"]
        invert = binding.get("invert", False)

        # Get bound entity state
        state = self.hass.states.get(bound_entity_id)
        if not state:
            _LOGGER.debug("Bound entity %s not found", bound_entity_id)
            return

        # Map state to LED on/off
        should_be_on = STATE_TO_LED.get(state.state, False)
        if invert:
            should_be_on = not should_be_on

        # Call switch service to update LED
        service = "turn_on" if should_be_on else "turn_off"

        _LOGGER.debug(
            "LED sync: %s (%s) → %s (%s) [invert=%s]",
            bound_entity_id,
            state.state,
            led_entity_id,
            "ON" if should_be_on else "OFF",
            invert,
        )

        await self.hass.services.async_call(
            "switch",
            service,
            {"entity_id": led_entity_id},
            blocking=False,
        )

    async def async_reload(self) -> None:
        """Reload bindings from config entry options."""
        # Remove all listeners
        for remove_listener in self._listeners.values():
            remove_listener()
        self._listeners.clear()

        # Reload bindings
        self._load_bindings()
        await self._register_all_listeners()

        _LOGGER.info("LED bindings reloaded: %d active bindings", len(self._bindings))

    async def async_unload(self) -> None:
        """Remove all listeners."""
        for remove_listener in self._listeners.values():
            remove_listener()
        self._listeners.clear()
        _LOGGER.info("LED binding manager unloaded")
```

### 2. LED Binding Options Flow Handler (`config_flow/led_bindings.py`)

**Purpose:** UI for configuring LED bindings

```python
"""LED Binding configuration handler."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from ..const import (
    DOMAIN,
    CONF_DIMMERS,
    CONF_LED_BINDINGS,
    BINDABLE_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)


class LEDBindingHandler:
    """Handler for LED binding configuration."""

    def __init__(self, options_flow):
        """Initialize the LED binding handler."""
        self.flow = options_flow

    async def async_step_led_binding_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show LED binding management menu."""
        dimmers = self.flow.config_entry.data.get(CONF_DIMMERS, [])

        if not dimmers:
            return self.flow.async_abort(reason="no_dimmers_configured")

        if user_input is not None:
            dimmer_name = user_input.get("dimmer_to_configure")

            # Store selected dimmer for next step
            self.flow._selected_dimmer = dimmer_name
            return await self.async_step_configure_dimmer_leds()

        # Build dimmer selection
        dimmer_options = [
            {
                "label": f"{d.get('name')} ({d.get('button_count')} buttons)",
                "value": d.get("name")
            }
            for d in dimmers
        ]

        schema = vol.Schema({
            vol.Required("dimmer_to_configure"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=dimmer_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.flow.async_show_form(
            step_id="led_binding_menu",
            data_schema=schema,
        )

    async def async_step_configure_dimmer_leds(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure LED bindings for selected dimmer."""
        dimmer_name = self.flow._selected_dimmer

        # Find dimmer config
        dimmers = self.flow.config_entry.data.get(CONF_DIMMERS, [])
        dimmer = next((d for d in dimmers if d.get("name") == dimmer_name), None)

        if not dimmer:
            return self.flow.async_abort(reason="dimmer_not_found")

        button_count = dimmer.get("button_count", 2)

        if user_input is not None:
            # Save bindings
            bindings = {}

            for btn_num in range(1, button_count + 1):
                entity_id = user_input.get(f"button_{btn_num}_entity")
                invert = user_input.get(f"button_{btn_num}_invert", False)

                if entity_id:
                    bindings[str(btn_num)] = {
                        "entity_id": entity_id,
                        "invert": invert,
                    }
                else:
                    bindings[str(btn_num)] = None

            # Save to config entry options
            current_options = dict(self.flow.config_entry.options)
            led_bindings = current_options.get(CONF_LED_BINDINGS, {})
            led_bindings[dimmer_name] = bindings
            current_options[CONF_LED_BINDINGS] = led_bindings

            self.flow.hass.config_entries.async_update_entry(
                self.flow.config_entry,
                options=current_options
            )

            _LOGGER.info(
                "Updated LED bindings for dimmer '%s': %d buttons configured",
                dimmer_name,
                sum(1 for b in bindings.values() if b is not None)
            )

            # Reload LED binding manager
            await self._reload_led_binding_manager()

            # Clear temp state
            del self.flow._selected_dimmer

            return self.flow.async_create_entry(title="", data={})

        # Build dynamic form
        schema_fields = {}

        # Get existing bindings
        existing_bindings = self.flow.config_entry.options.get(CONF_LED_BINDINGS, {}).get(dimmer_name, {})

        for btn_num in range(1, button_count + 1):
            existing = existing_bindings.get(str(btn_num), {})

            # Entity selector (domain-filtered)
            schema_fields[vol.Optional(f"button_{btn_num}_entity", default=existing.get("entity_id"))] = (
                selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=list(BINDABLE_DOMAINS.keys())
                    )
                )
            )

            # Invert checkbox
            schema_fields[vol.Optional(f"button_{btn_num}_invert", default=existing.get("invert", False))] = (
                selector.BooleanSelector()
            )

        schema = vol.Schema(schema_fields)

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
        entry_data = self.flow.hass.data[DOMAIN].get(self.flow.config_entry.entry_id)

        if entry_data and "led_binding_manager" in entry_data:
            led_manager = entry_data["led_binding_manager"]
            await led_manager.async_reload()
```

### 3. Update `__init__.py` - Register LED Binding Manager

```python
# At top:
from .led_binding_manager import LEDBindingManager

# In async_setup_entry:
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... existing hub setup ...

    # Initialize LED binding manager (v1.22.0+)
    led_manager = LEDBindingManager(hass, hub, entry)
    await led_manager.async_setup()

    # Store manager in entry data
    hass.data[DOMAIN][entry.entry_id]["led_binding_manager"] = led_manager

    # ... rest of setup ...

# In async_unload_entry:
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... existing unload ...

    # Cleanup LED binding manager
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data and "led_binding_manager" in entry_data:
        led_manager = entry_data["led_binding_manager"]
        await led_manager.async_unload()

    # ... rest of unload ...
```

### 4. Update `const.py` - Add LED Binding Constants

```python
# LED Binding configuration (v1.22.0+)
CONF_LED_BINDINGS = "led_bindings"  # Stored in config_entry.options
CONF_INVERT = "invert"

# BINDABLE_DOMAINS already exists in const.py
# STATE_TO_LED already exists in const.py
```

### 5. Update Config Flow to Add LED Binding Menu

In `config_flow/flow.py` or wherever the options menu is defined:

```python
from .led_bindings import LEDBindingHandler

class CrestronOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        self.config_entry = config_entry
        self._led_binding_handler = LEDBindingHandler(self)

    async def async_step_init(self, user_input=None):
        """Main options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "manage_entities",
                "manage_dimmers",
                "led_binding_menu",  # NEW: LED binding configuration
                "manage_join_sync",
            ],
        )

    async def async_step_led_binding_menu(self, user_input=None):
        """Delegate to LED binding handler."""
        return await self._led_binding_handler.async_step_led_binding_menu(user_input)

    async def async_step_configure_dimmer_leds(self, user_input=None):
        """Delegate to LED binding handler."""
        return await self._led_binding_handler.async_step_configure_dimmer_leds(user_input)
```

---

## Blueprint Solution (After LED Binding Implementation)

Once LED binding is handled by the integration, **simplify the blueprint to ONLY handle button actions**:

```yaml
blueprint:
  name: Crestron Dimmer/Keypad Button Controller
  description: >
    Configure actions for Crestron dimmer/keypad button presses.
    LED binding is configured via Integration → Configure → LED Bindings.

  input:
    button_entity:
      name: Button Event Entity (Required)
      description: Select ANY button event entity from your dimmer
      selector:
        entity:
          filter:
            - domain: event
              integration: crestron

    # Actions for all 6 buttons × 3 press types (18 total)
    button_1_press:
      name: "Button 1 - Press Action"
      default: []
      selector:
        action: {}
    # ... repeat for all buttons/press types ...

trigger:
  # Single required trigger - monitors all buttons
  - platform: state
    entity_id: !input button_entity

action:
  - variables:
      event_type: "{{ trigger.to_state.attributes.get('event_type', '') }}"
      button_num: "{{ trigger.to_state.attributes.get('button', 0) | int }}"

  - choose:
      - conditions:
          - "{{ button_num == 1 and event_type == 'press' }}"
        sequence: !input button_1_press
      # ... repeat for all combinations ...
    default: []
```

**Why this works:**
- Only ONE required trigger (no optional entity triggers)
- Empty action sequences (`[]`) don't cause errors
- All routing based on event attributes (`button`, `event_type`)
- LED binding completely handled by integration (no triggers needed)

---

## Implementation Order

1. **Create `led_binding_manager.py`** with core LED sync logic
2. **Create `config_flow/led_bindings.py`** with UI flow
3. **Update `__init__.py`** to register LED binding manager
4. **Update `const.py`** with new constants
5. **Update config flow** to add LED binding menu option
6. **Test LED binding** configuration and state sync
7. **Simplify blueprint** to remove LED binding triggers
8. **Update documentation** (README, CHANGELOG)
9. **Commit and release** as v1.22.0

---

## Testing Checklist

- [ ] Create new LED binding via Options Flow
- [ ] Verify binding saved in config entry options
- [ ] Verify state listener registered
- [ ] Change bound entity state → LED updates
- [ ] Test invert flag (LED on when entity off)
- [ ] Edit existing binding
- [ ] Remove binding (set to blank)
- [ ] Test multiple dimmers independently
- [ ] Verify bindings persist after HA restart
- [ ] Test unload/reload of integration
- [ ] Verify no entity registry bloat (no select entities created)
- [ ] Verify no database errors (no 32KB warnings)

---

## Migration Path (Optional)

Users with old select entities can be migrated automatically:

1. On integration setup, detect old select entities
2. Read binding from select entity state
3. Save to config entry options
4. Remove old select entity from entity registry
5. Show notification about migration

Alternatively, just show a notification directing users to reconfigure via Options Flow.

---

## Estimated Effort

**4-6 hours** including:
- Implementation: 3-4 hours
- Testing: 1-2 hours
- Documentation: 30 minutes

---

## Benefits Summary

✅ **No database bloat** - Zero select entities created
✅ **No 32KB errors** - Config stored in JSON, not entity registry
✅ **Clean UI** - Domain filtering shows only 15-50 relevant entities
✅ **Fast & reliable** - Direct state listeners, O(1) lookups
✅ **Persistent** - Survives HA restart (config entry storage)
✅ **No blueprint limitations** - Core integration logic
✅ **Familiar UX** - Uses standard HA entity selector
✅ **Maintainable** - Clean separation of concerns
✅ **Flexible** - Supports all domains, invert logic, multiple dimmers

---

## Next Steps

**Ready to implement!** Follow the implementation order above, starting with `led_binding_manager.py`.
