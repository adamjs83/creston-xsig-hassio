# Crestron XSIG Integration for Home Assistant

[![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)](https://github.com/adamjs83/crestron_custom_component/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Home Assistant custom component for integrating with Crestron control systems using the XSIG (External Signal) protocol. This integration provides bidirectional communication with Crestron processors, allowing Home Assistant to control and monitor Crestron devices.

## Features

- **YAML-based configuration** for flexible setup
- **Bidirectional join communication** (digital, analog, and serial)
- **Multiple platform support**: lights, switches, climate, covers, media players, sensors, binary sensors
- **Template-based state synchronization** (Home Assistant → Crestron)
- **Script execution** from join changes (Crestron → Home Assistant)
- **Automatic reconnection** on connection loss

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/adamjs83/crestron_custom_component`
6. Category: Integration
7. Click "Add"
8. Find "Crestron XSIG Integration" and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/crestron` directory to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

All configuration is done via `configuration.yaml`. There is no UI configuration flow.

### Basic Configuration

```yaml
crestron:
  port: 16384  # The port number configured in your XSIG symbol
```

### Hub-Level Join Synchronization

#### Sending Data TO Crestron (to_joins)

Automatically sync Home Assistant states to Crestron joins:

```yaml
crestron:
  port: 16384
  to_joins:
    # Sync entity state to digital join
    - join: d1
      entity_id: light.kitchen

    # Sync entity attribute to analog join
    - join: a1
      entity_id: light.kitchen
      attribute: brightness

    # Use value template for complex logic
    - join: d2
      value_template: "{{ is_state('sun.sun', 'above_horizon') }}"

    # Sync multiple entities
    - join: a2
      value_template: "{{ state_attr('climate.living_room', 'current_temperature') | int }}"
```

#### Receiving Data FROM Crestron (from_joins)

Execute scripts or services when Crestron join values change:

```yaml
crestron:
  port: 16384
  from_joins:
    # Execute script on button press (digital join)
    - join: d100
      script:
        - service: light.toggle
          target:
            entity_id: light.kitchen

    # Call service with analog join value
    - join: a100
      script:
        - service: input_number.set_value
          target:
            entity_id: input_number.crestron_slider
          data:
            value: "{{ value }}"

    # Multiple actions
    - join: d101
      script:
        - service: light.turn_on
          target:
            entity_id: light.living_room
        - service: media_player.turn_on
          target:
            entity_id: media_player.tv
```

### Platform Configuration

#### Light

```yaml
light:
  - platform: crestron
    name: Kitchen Light
    join: d1                    # On/off digital join
    brightness_join: a1         # Optional: brightness analog join (0-255)
```

#### Switch

```yaml
switch:
  - platform: crestron
    name: Fountain Pump
    switch_join: d10
```

#### Climate (Thermostat)

Standard HVAC:
```yaml
climate:
  - platform: crestron
    name: Living Room HVAC
    is_on_join: d20            # System on/off
    heat_sp_join: a20          # Heat setpoint (in tenths, e.g., 720 = 72.0°F)
    cool_sp_join: a21          # Cool setpoint
    reg_temp_join: a22         # Current temperature feedback
    mode_heat_join: d21        # Mode: Heat
    mode_cool_join: d22        # Mode: Cool
    mode_auto_join: d23        # Mode: Auto
    mode_off_join: d24         # Mode: Off
    fan_on_join: d25           # Fan: On
    fan_auto_join: d26         # Fan: Auto
```

Floor warming thermostat:
```yaml
climate:
  - platform: crestron
    name: Bathroom Floor Heat
    floor_mode_join: a30       # Set mode: 1=Off, 2=Heat
    floor_mode_fb_join: a31    # Mode feedback
    floor_sp_join: a32         # Setpoint (tenths)
    floor_sp_fb_join: a33      # Setpoint feedback
    floor_temp_join: a34       # Current temperature
```

#### Cover (Shades/Blinds)

```yaml
cover:
  - platform: crestron
    name: Living Room Shade
    join: d30                  # Open command
    is_opening_join: d31       # Optional: opening state feedback
    is_closing_join: d32       # Optional: closing state feedback
    is_closed_join: d33        # Optional: closed state feedback
    stop_join: d34             # Optional: stop command
    pos_join: a30              # Optional: position control (0-100)
```

#### Media Player

```yaml
media_player:
  - platform: crestron
    name: Living Room TV
    join: d40                  # Power
    mute_join: d41             # Mute
    volume_join: a40           # Volume level
    source_number_join: a41    # Source selection
    sources:
      - name: Cable
      - name: Blu-ray
      - name: AppleTV
      - name: Streaming
```

#### Sensor

```yaml
sensor:
  - platform: crestron
    name: Outdoor Temperature
    value_join: a50            # Analog join with value
    divisor: 10                # Optional: divide by 10 (for tenths)
    unit_of_measurement: "°F"
```

#### Binary Sensor

```yaml
binary_sensor:
  - platform: crestron
    name: Front Door
    join: d50                  # Digital join
    device_class: door         # Optional: door, window, motion, etc.
```

## Complete Example

```yaml
crestron:
  port: 16384
  to_joins:
    # Sync HA states to Crestron
    - join: d1
      entity_id: light.kitchen
    - join: a1
      entity_id: light.kitchen
      attribute: brightness
  from_joins:
    # React to Crestron button presses
    - join: d100
      script:
        - service: light.toggle
          target:
            entity_id: light.kitchen

light:
  - platform: crestron
    name: Kitchen Light
    join: d1
    brightness_join: a1

climate:
  - platform: crestron
    name: Living Room
    is_on_join: d20
    heat_sp_join: a20
    cool_sp_join: a21
    reg_temp_join: a22
    mode_heat_join: d21
    mode_cool_join: d22
    mode_auto_join: d23
    mode_off_join: d24
    fan_on_join: d25
    fan_auto_join: d26

cover:
  - platform: crestron
    name: Living Room Shade
    join: d30
    pos_join: a30
```

## Crestron Programming

On the Crestron side, add an XSIG symbol to your program:

1. Drag an "Ethernet Intersystem Communication" symbol (XSIG) into your program
2. Configure the XSIG properties:
   - Set the port number (must match the `port` in your configuration)
   - Map digital, analog, and serial signals as needed
3. Connect the XSIG signals to your logic
4. Compile and load the program

### Join Number Reference

- **Digital joins (d)**: True/false, on/off, button presses
- **Analog joins (a)**: Numeric values (0-65535)
  - Temperature setpoints: multiply by 10 (e.g., 72.5°F = 725)
  - Brightness: 0-255
  - Position: 0-100
- **Serial joins (s)**: Text strings

## Troubleshooting

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.crestron: debug
```

### Common Issues

1. **Connection fails**: Verify the port number matches your XSIG symbol configuration
2. **No state updates**: Check that joins are properly mapped in both HA and Crestron
3. **Values incorrect**: For temperatures, remember to use tenths (multiply by 10)
4. **Template errors**: Verify template syntax and entity IDs in `to_joins`

## Credits

This component is forked from the excellent work by [@npope](https://github.com/npope) - [home-assistant-crestron-component](https://github.com/npope/home-assistant-crestron-component)

### Enhancements in this fork:
- HACS compatibility and automated releases
- Enhanced climate platform with floor warming support
- Improved documentation and examples
- Additional join configuration options
- Active maintenance and updates

Thank you to @npope for creating the original integration!

## License

MIT License - see LICENSE file for details

## Contributing

Pull requests and issues welcome! Please test thoroughly before submitting.
