# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
