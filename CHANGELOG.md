# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


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
