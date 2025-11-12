# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).






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
