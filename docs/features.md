# Features

Covers: Core capabilities, supported platforms, dimmer/keypad and advanced features.
Last verified: 2026-11-22 (split from README.md; content not re-verified)

## Features

### Core Capabilities

- **Bidirectional Communication** - Full support for digital, analog, and serial joins
- **UI-Based Setup** - Configure everything through Home Assistant's interface
- **YAML Import** - Automatic migration from existing YAML configurations
- **Template Sync** - Synchronize HA states to Crestron for feedback
- **Script Execution** - Run HA services when Crestron join values change
- **Auto Reconnect** - Automatic connection recovery on network issues

### Supported Platforms

- **Lights** - On/off and dimmable lights with brightness control
- **Switches** - Simple on/off control for any device
- **Climate** - HVAC thermostats and floor warming systems
- **Covers** - Shades, blinds, and curtains with position control
- **Media Players** - Control AV equipment with source selection
- **Sensors** - Monitor analog values (temperature, humidity, etc.)
- **Binary Sensors** - Monitor digital states (doors, motion, etc.)
- **Dimmers/Keypads** - Full Crestron keypad support with button events
- **Button Events** - Press, double-press, and hold detection

### Dimmer/Keypad Features

Complete support for Crestron keypads and dimmers:

- **Button Events** - Detect press, double-press, and hold actions
- **LED Binding** - Automatic LED feedback from any HA entity
- **LED Control** - Direct LED on/off control
- **Lighting Loads** - Optional dimmer control with single analog join
- **Auto-Sequential Joins** - Simple configuration with automatic join assignment
- **Manual Join Assignment** - Advanced mode for custom join layouts
- **2-6 Buttons** - Support for any keypad size

### Advanced Features

- **Modern Entity Naming** - Context-aware names that follow HA standards
- **Device Grouping** - Related entities grouped under parent devices
- **Entity Management** - Add, edit, remove entities via UI
- **Join Management** - Configure to_joins and from_joins through UI
- **No Hub Disruption** - Hub stays connected when managing entities
- **Dual Config Support** - YAML and UI configurations coexist
