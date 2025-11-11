# Crestron XSIG Integration for Home Assistant

This custom component provides integration between Home Assistant and Crestron control systems using the XSIG (External Signal) protocol.

## Features

- **YAML-based configuration** for maximum flexibility
- **Bidirectional communication** with Crestron processors
- **Multiple platform support**: lights, switches, climate, covers, media players, sensors, and binary sensors
- **Template-based join mapping** for dynamic state synchronization
- **Script execution** from Crestron join changes

## Supported Platforms

- 💡 **Lights** - Control lighting with brightness and on/off
- 🔌 **Switches** - Simple on/off control
- 🌡️ **Climate** - HVAC control with temperature, modes, and fan settings
- 🪟 **Covers** - Shades, blinds, and other covering controls
- 📺 **Media Players** - Audio/video control with sources and volume
- 📊 **Sensors** - Analog value monitoring
- 🔘 **Binary Sensors** - Digital state monitoring

## Installation via HACS

1. Add this repository as a custom repository in HACS
2. Search for "Crestron XSIG Integration" in HACS
3. Click Install
4. Restart Home Assistant
5. Configure via `configuration.yaml`

## Quick Start

Add to your `configuration.yaml`:

```yaml
crestron:
  port: 16384  # XSIG port on your processor
```

For detailed configuration examples, see the [README](https://github.com/adamjs83/crestron_custom_component/blob/main/README.md).

## Requirements

- Home Assistant 2024.1.0 or newer
- Crestron processor with XSIG symbol configured
- Network connectivity between Home Assistant and Crestron processor

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/adamjs83/crestron_custom_component/issues).
