# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.17.4] - 2025-11-18

### Fixed
- **Entity Naming** - All dimmer entities now include dimmer name for better organization
  - Event entities: "{Dimmer Name} Button 1" instead of "Button 1"
  - Select entities: "{Dimmer Name} LED 1 Binding" instead of "LED 1 Binding"
  - Switch entities: Already correct - "{Dimmer Name} LED 1"
  - Light entities: Already correct - "{Dimmer Name} Light"

### Changed
- Updated `event.py`: Changed entity name from f"Button {button_num}" to f"{dimmer_name} Button {button_num}"
- Updated `select.py`: Changed entity name from f"LED {button_num} Binding" to f"{dimmer_name} LED {button_num} Binding"

## [1.17.3] - 2025-11-18

### Fixed
- **Dimmer Lighting Load** - Removed unnecessary digital on/off join; dimmers now use single analog join (0-65535) for both on/off and brightness control
- **Device Grouping** - Dimmer lighting load entities now properly grouped under dimmer device in Home Assistant

### Changed
- Lighting load configuration simplified - only requires brightness join (analog), no separate on/off join
- Light entities from dimmers use unique_id format: `crestron_light_dimmer_{name}_a{join}`
- Updated cleanup code to use brightness_join instead of obsolete is_on_join
- Updated UI strings and descriptions to reflect single analog join requirement
- Updated README with correct Crestron programming instructions (single analog join for dimmer control)

### Technical Details
- Light platform (`light.py`) now creates entities from dimmer configs with device grouping
- Config flow no longer asks for `light_on_join`, only `light_brightness_join`
- Dimmer lights automatically grouped under parent dimmer device
- Analog join range: 0 (off), 1-65535 (on with varying brightness)

## [1.17.2] - 2025-11-18

### Fixed
- **Dimmer Device Cleanup** - Device now properly removed from device registry when dimmer is deleted
- **Complete Entity Removal** - All entity types now removed when dimmer is deleted (events, selects, LED switches, light)
- Fixed issue where only light entity was removed, leaving orphaned event, select, and switch entities

### Changed
- Enhanced `_cleanup_dimmer_entities()` to remove all associated entity types:
  - Event entities (button press events)
  - Select entities (LED bindings)
  - Switch entities (LED switches)
  - Light entity (if lighting load present)
  - Device from device registry
- Cleanup now runs for ALL dimmers, not just those with lighting loads

## [1.17.1] - 2025-11-18

### Added
- **Manual Join Assignment Mode** - Choose between auto-sequential or manual join assignment
- Mode selector before dimmer configuration (auto-sequential recommended, manual for advanced users)
- Manual mode allows non-sequential join assignments (e.g., d10, d20, d30 instead of d10, d11, d12)
- Dynamic form that shows only relevant button join fields based on button count

### Changed
- Dimmer configuration now has 2-step process: 1) Select mode, 2) Configure joins
- Entity platforms (event.py, switch.py) now handle both auto-sequential and manual join modes

### Technical Details
- Added async_step_add_dimmer_mode() for mode selection
- Added async_step_add_dimmer_manual() for manual join configuration
- Dimmer config stores "manual_joins" dict for manual mode or "base_join" for auto mode
- Entity creation checks for manual_joins first, falls back to base_join calculation
- Form dynamically generates 3 fields per button (press, double, hold)

## [1.17.0] - 2025-11-18

### Added - Complete Dimmer/Keypad Redesign
- **Event Platform** - New platform for button press events (press, double_press, hold)
- **Select Platform** - LED binding dropdowns to sync LEDs with any HA entity
- **Simple Configuration** - Single form replaces multi-step wizard
- **Sequential Join Assignment** - Enter base join, system auto-assigns remaining joins
- **Real Entity Integration** - Creates event, switch, select, and light entities
- **LED Binding System** - Dropdown lists all HA entities, LED follows state automatically
- **Device Registry** - All entities grouped under single device

### Changed - Breaking Changes
- Simplified configuration from multi-step to single form (4 fields)
- Button actions configured via HA automations (not config flow)
- LED feedback configured via select dropdown (not config flow)
- Join assignment: 3 joins per button (press d10, double d11, hold d12)

### Removed
- v1.16.x dimmer configuration (multi-step wizard) - marked as deprecated

### Technical Details
- Event entities fire: event_type="crestron_button" with action: press/double_press/hold
- LED switches use press join for OUTPUT (bidirectional join usage)
- Select entities scan entity registry for bindable domains
- State mapping: 15+ domains, 30+ state mappings to LED on/off
- Sequential validation: base join + (button_count * 3 - 1) must be <= 250

## [1.16.4] - 2025-11-18 [DEPRECATED]

### Deprecated
- This version's dimmer/keypad implementation is replaced by v1.17.0
- Multi-step wizard configuration removed in favor of simple single-form approach
- Use v1.17.0 for new installations

### Added
- **Button number display** in dimmer configuration - Form title now shows "Configure Button X of Y"
- **Optional press action** - Press action now has an enable checkbox like double press and hold
- Comprehensive UI strings for all dimmer configuration steps

### Fixed
- Button configuration forms now display which button is being configured
- Press action is now truly optional with enable/disable checkbox
- All dimmer configuration steps have proper titles and descriptions

### Technical Details
- Added strings.json entries for add_dimmer_basic, add_dimmer_lighting, add_dimmer_button
- Button title uses description_placeholders: "Configure Button {button_num} of {total_buttons}"
- Added config_press checkbox to button schema (matches config_double_press and config_hold pattern)
- Press validation now checks config_press flag before requiring press_join
- Translations synchronized to en.json

## [1.16.3] - 2025-11-18

### Fixed
- Fixed "Unknown error occurred" when submitting dimmer configuration forms
- Removed unsupported `placeholder` parameter from TextSelectorConfig instances
- Error: `extra keys not allowed @ data['placeholder']`

### Technical Details
- TextSelectorConfig does not support the `placeholder` parameter in Home Assistant
- Changed all TextSelector instances to use `type=selector.TextSelectorType.TEXT` pattern
- Fixed in both button configuration (7 instances) and lighting load configuration (2 instances)
- This fixes the validation error that prevented dimmer configuration forms from submitting

## [1.16.2] - 2025-11-18

### Fixed
- Fixed "Unknown error occurred" when clicking "Add Dimmer/Keypad"
- Changed button count selector values from integers to strings (Home Assistant requirement)
- Added proper string-to-integer conversion when processing button count

### Technical Details
- SelectSelector values must be strings, not integers
- Updated CONF_BUTTON_COUNT selector options to use string values ("2", "3", "4", "5", "6")
- Added `int()` conversion when reading button_count from user input
- This fixes the silent form validation failure that caused the "Unknown error" message

## [1.16.1] - 2025-11-18

### Fixed
- Added debug logging to dimmer configuration flow to troubleshoot "Unknown error occurred" issue
- Added logging to async_step_dimmer_menu and async_step_add_dimmer_basic for diagnostics

### Technical Details
- Debug logs will show when dimmer menu is accessed and which actions are selected
- Helps identify where configuration flow is failing during dimmer creation

## [1.16.0] - 2025-11-18

### Added
- **Dimmer/Keypad Configuration Manager** - Complete UI-based configuration for Crestron dimmers and keypads
- Third main menu option: "Manage Dimmers/Keypads" with full add/edit/remove capabilities
- Dynamic button configuration supporting 2-6 buttons per dimmer/keypad
- Optional lighting load configuration with on/off and brightness control
- Button action types: Press, Double Press, and Hold (all optional and independent)
- Button feedback configuration for syncing HA state to Crestron button LEDs
- Entity picker for button actions with domain-aware action selection
- Service data parameter support via YAML input for advanced service calls
- Comprehensive join conflict detection across all entities and dimmers
- Automatic entity registry cleanup when dimmers are removed
- 13 domain action mappings: light, switch, cover, climate, media_player, fan, lock, vacuum, scene, script, input_boolean, automation, group

### Changed
- Enhanced main menu from 3 to 4 items including dimmer management
- Dimmer button actions automatically generate from_joins (Crestron → HA service calls)
- Dimmer button feedback automatically generates to_joins (HA state → Crestron)
- Runtime processing merges dimmer-generated joins with explicit joins
- All dimmer configurations stored in config entry data (CONF_DIMMERS)

### Technical Details
- No platform changes required - uses existing hub.py and light.py implementations
- Dimmer processing in __init__.py converts button configs to from_joins/to_joins at runtime
- Each button supports independent press/double press/hold actions with custom service data
- Lighting load entities use unique_id pattern: `crestron_light_dimmer_{join}`
- Join validation includes dimmers in conflict checking algorithm
- Added 9 new constants to const.py for dimmer configuration
- Added 600+ lines to config_flow.py with 8 new async methods
- DOMAIN_ACTIONS dictionary provides action options for 13 entity domains

## [1.15.0] - 2025-11-18

### Changed
- **Restructured Configuration Menu for Better UX** - Complete redesign of the options flow navigation
- Main menu reduced from 12 items to 3 items for better usability
- Two-menu hierarchy: "Manage Entities" and "Manage Join Syncs"
- Entity management submenu: Add/Edit/Remove entities with entity type selection
- Join sync management submenu: Add/Edit/Remove to_joins and from_joins
- Back navigation at every menu level for intuitive user experience
- Live counts displayed in menu labels showing configured entities and joins

### Technical Details
- Added async_step_entity_menu() for entity management submenu
- Added async_step_select_entity_type() for entity type selection
- Added async_step_join_menu() for join sync management submenu
- All existing Add/Edit/Remove flows unchanged - only navigation restructured
- Improves cognitive load by separating entities from join syncs
- Scalable architecture for future entity platform additions

## [1.14.0] - 2025-01-18

### Added
- **UI Configuration for Standard HVAC Climate Entities** - Complete UI-based entity management for standard thermostats
- Climate type selection: Floor Warming or Standard HVAC
- Standard HVAC form with 20 join fields (3 analog + 15 digital required + 2 digital optional)
- Organized form sections: Temperature Setpoints, HVAC Modes, Fan Modes, Equipment Status, HVAC Actions
- Automatic routing to correct climate form when editing based on entity type
- Type-aware entity display in edit/remove lists showing "Floor Warming" vs "Standard HVAC"

### Changed
- Enhanced climate.py to support both floor_warming and standard types in async_setup_entry
- Updated config_flow.py with async_step_select_climate_type and async_step_add_climate_standard
- Climate menu label updated to reflect both type options
- Added all standard HVAC join constants to config_flow.py imports

### Technical Details
- Full support for both climate types via UI (no YAML required)
- Standard HVAC joins: heat_sp, cool_sp, reg_temp, mode_heat, mode_cool, mode_auto, mode_heat_cool, mode_off, fan_on, fan_auto, fan_mode_on, fan_mode_auto, h1, h2 (opt), c1, c2 (opt), fa, hvac_action_heat, hvac_action_cool, hvac_action_idle
- Optional joins (h2, c2) validated only if provided
- Hub persistence during entity management (no connection drops)
- Safe reload handling with ValueError fallback

## [1.13.0] - 2025-01-18

### Added
- **UI Configuration for Climate Entities (Floor Warming)** - Complete UI-based entity management for floor warming thermostats
- Add/edit/remove climate entities through the options flow without editing YAML
- Support for 5 analog joins: floor_mode_join, floor_mode_fb_join, floor_sp_join, floor_sp_fb_join, floor_temp_join
- Join validation for analog format ("aXX")
- Automatic entity registry cleanup when climate entities removed via UI
- UI/YAML coexistence with unique_id prefixes ("ui" vs "yaml")

### Changed
- Updated climate.py to support from_ui parameter for unique_id differentiation
- Enhanced config_flow.py with async_step_add_climate, edit, and remove flows
- Added CONF_CLIMATES constant to const.py

### Technical Details
- Floor warming thermostat support only (standard HVAC thermostats still YAML-only)
- Follows established pattern from previous platforms
- Hub persistence during entity management (no connection drops)
- Safe reload handling with ValueError fallback

### Limitations
- Standard HVAC thermostats (with heat/cool setpoints, modes, fan controls) remain YAML-only due to complexity
- Only floor_warming type climate entities can be configured via UI

## [1.12.0] - 2025-01-17

### Added
- **UI Configuration for Switches** - Complete UI-based entity management for switches via Configure button
- Add/edit/remove switch entities through the options flow without editing YAML
- Switch join input with validation (digital format "dXX")
- Device class selector: Switch or Outlet
- Automatic entity registry cleanup when switches removed via UI
- UI/YAML coexistence with unique_id prefixes ("ui" vs "yaml")
- Auto-request join status on entity creation for immediate state sync

### Changed
- Updated switch.py to support from_ui parameter for unique_id differentiation
- Enhanced config_flow.py with async_step_add_switch, edit, and remove flows
- Added CONF_SWITCHES constant to const.py
- Fixed switch is_on property to default to False instead of None when no data available

### Technical Details
- Hub persistence during entity management (no connection drops)
- Follows established pattern from lights (v1.11.0), covers (v1.8.0), binary sensors (v1.9.0), and sensors (v1.10.0)
- Safe reload handling with ValueError fallback
- Immediate state synchronization via request_update()

### Roadmap Progress
- ✅ Covers (v1.8.0)
- ✅ Binary Sensors (v1.9.0)
- ✅ Sensors (v1.10.0)
- ✅ Light (v1.11.0)
- ✅ Switch (v1.12.0)
- 🔲 Climate (next)
- 🔲 Media Player

## [1.11.2] - 2025-01-17

### Added
- **Auto-request join status on entity creation** - Entities now automatically request current state from Crestron when added
- New `request_update()` method in CrestronXsig hub to trigger state updates from Crestron
- Immediate state synchronization for newly created UI entities (lights, covers, sensors, binary sensors)

### Changed
- Updated all platform entities (light, cover, sensor, binary_sensor) to request updates when added to Home Assistant
- Entities created via UI now show correct state immediately without needing physical toggle
- Added debug logging for update requests

### Technical Details
- Added CrestronXsig.request_update() method that sends 0xFD command to Crestron
- Modified async_added_to_hass() in light.py, cover.py, sensor.py, binary_sensor.py
- Update request only sent if Crestron is connected (hub.is_available())
- Maintains same XSIG protocol behavior as initial connection

### User Impact
- No more "unknown" or "off" states for newly created entities
- Entities immediately reflect actual Crestron state
- Eliminates need to toggle physical switches after creating UI entities

## [1.11.1] - 2025-01-17

### Fixed
- **Light state showing as "unknown"** - Fixed is_on property to default to False instead of None when no Crestron value available and no restored state
- Newly created UI lights now show as "off" instead of "unknown" until first value received from Crestron

### Technical Details
- Changed light.py line 181: return False as default instead of None
- Prevents "unknown" state for lights on first setup
- Matches behavior of onoff-type lights

## [1.11.0] - 2025-01-17

### Added
- **UI Configuration for Lights** - Complete UI-based entity management for lights via Configure button
- Add/edit/remove light entities through the options flow without editing YAML
- Brightness join input with validation (analog format "aXX")
- Light type selector: "Dimmable (Brightness)" or "On/Off Only"
- Automatic entity registry cleanup when lights removed via UI
- UI/YAML coexistence with unique_id prefixes ("ui" vs "yaml")

### Changed
- Updated light.py to support from_ui parameter for unique_id differentiation
- Enhanced config_flow.py with async_step_add_light, edit, and remove flows
- Added CONF_LIGHTS constant to const.py

### Technical Details
- Hub persistence during entity management (no connection drops)
- Follows established pattern from covers (v1.8.0), binary sensors (v1.9.0), and sensors (v1.10.0)
- Safe reload handling with ValueError fallback
- Supports both ColorMode.BRIGHTNESS and ColorMode.ONOFF

### Roadmap Progress
- ✅ Covers (v1.8.0)
- ✅ Binary Sensors (v1.9.0)
- ✅ Sensors (v1.10.0)
- ✅ Light (v1.11.0)
- 🔲 Switch (next)
- 🔲 Climate
- 🔲 Media Player

## [1.10.0] - 2025-01-17

### Added
- **UI Configuration for Sensors** - Complete UI-based entity management for sensors via Configure button
- Add/edit/remove sensor entities through the options flow without editing YAML
- Analog join (value_join) input with validation (e.g., "a10")
- Device class selector: temperature, humidity, pressure, power, energy, voltage, current, illuminance, battery, none
- Unit of measurement configuration field
- Divisor support for value scaling (e.g., temperature tenths: 720 = 72.0°F)
- Automatic entity registry cleanup when sensors removed via UI
- UI/YAML coexistence with unique_id prefixes ("ui" vs "yaml")

### Changed
- Updated sensor.py to support from_ui parameter for unique_id differentiation
- Enhanced config_flow.py with async_step_add_sensor, edit, and remove flows
- Added CONF_SENSORS constant to const.py

### Technical Details
- Hub persistence during entity management (no connection drops)
- Follows established pattern from covers (v1.8.0) and binary sensors (v1.9.0)
- Safe reload handling with ValueError fallback

### Roadmap Progress
- ✅ Covers (v1.8.0)
- ✅ Binary Sensors (v1.9.0)
- ✅ Sensors (v1.10.0)
- 🔲 Light (next)
- 🔲 Switch
- 🔲 Climate
- 🔲 Media Player





## [1.5.5] - 2025-11-11

### Changed
- Fix cover direction lock after stop - clear analog state

## [1.5.4] - 2025-11-11

### Changed
- Fix cover stop functionality - ensure signals are transmitted

## [1.5.3] - 2025-11-11

### Changed
- Fix event loop error in cover stop (use asyncio.sleep)

## [1.5.2] - 2025-11-11

### Changed
- Fix event loop error in cover stop action

## [1.5.1] - 2025-11-11

### Fixed
- **CRITICAL:** Fix AttributeError when device_info property accessed
- CrestronXsig object now properly stores port attribute
- Fixes compatibility issues with other integrations (e.g., versatile_thermostat)
- No breaking changes - purely additive fix

### Technical Details
- Added `self.port = None` to CrestronXsig.__init__()
- Added `self.port = port` to CrestronXsig.listen()
- Fixes: `AttributeError: 'CrestronXsig' object has no attribute 'port'`

### Impact
- All entity device_info properties now work correctly
- Device identifiers include port number as designed
- Zero user action required - automatic on upgrade

## [1.5.0] - 2025-11-11

### Changed
- Modernized platform loading to use current Home Assistant 2025.x patterns
- Replaced deprecated `async_load_platform` with proper `asyncio.gather` pattern
- Platforms now load in parallel with proper await (faster and more reliable)

### Fixed
- Eliminated deprecation warning for platform loading
- Device registry integration now properly creates "Crestron Control System" device
- Better error handling if platforms fail to load during startup

### Notes
- This is a non-breaking change - no user action required
- All entities maintain their existing IDs and functionality
- Upgrade from v1.4.0 is seamless - no configuration changes needed
- Device should now appear in Settings → Devices & Services → Devices
- Foundation for config flow implementation in v1.6.0

## [1.4.0] - 2025-11-11

### Added
- Device registry integration - all Crestron entities now appear under a single "Crestron Control System" device
- Device info metadata (manufacturer: Crestron Electronics, model: XSIG Gateway)
- Foundation for future config flow implementation

### Notes
- This is a purely additive change with no breaking changes
- All entities maintain their existing unique IDs and functionality
- Upgrade from v1.3.0 is seamless - no configuration changes required
- Device grouping improves UI organization and enables device-level diagnostics

## [1.3.0] - 2025-11-11

### Added
- Unique IDs for all entity types (light, switch, climate, cover, media_player, sensor, binary_sensor)
- Entity registry support enables UI-based entity renaming and customization
- Stable entity IDs that persist across Home Assistant restarts

### Notes
- This release restores unique ID functionality for users who downgraded from v1.2.x
- Existing entity registry entries will be automatically linked
- No configuration changes required

## [1.2.2] - 2025-11-11

### Fixed
- Fix ValueError: 'unavailable' is not a valid HVACMode in climate platform
- Properly validate restored HVAC mode states before using them
- Skip restoration of "unavailable" and "unknown" states

## [1.2.1] - 2025-11-11

### Fixed
- Fix socket exception when trying to send to Crestron before connection established
- Remove excessive debug logging that flooded logs (200+ messages)
- Add proper error handling around all socket write operations
- Mark connection as dead when socket write fails

## [1.2.0] - 2025-11-11

### Changed
- Phase 1: Critical functionality fixes - join tracking, RestoreEntity, unique IDs

## [1.1.2] - 2025-11-11

### Fixed
- Fix Home Assistant 2025.11 compatibility - remove deprecated STATE_* imports from cover platform

## [1.1.1] - 2025-11-11

### Changed
- Add missing sensor and switch platforms

## [1.1] - 2024-01-15

### Added
- Floor warming thermostat support with dedicated joins
- Additional climate joins for better HVAC state feedback
- Improved documentation and examples

### Changed
- Enhanced climate platform with more configuration options
- Better error handling and logging

### Fixed
- Template synchronization improvements
- Connection stability enhancements

## [1.0] - Initial Release

### Added
- Initial release with XSIG protocol support
- Platform support for: light, switch, climate, cover, media_player, sensor, binary_sensor
- Bidirectional join communication (digital, analog, serial)
- Template-based state synchronization (to_joins)
- Script execution from join changes (from_joins)
- Automatic reconnection handling
