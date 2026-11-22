# Platform configuration

Covers: Light, switch, climate, cover, media player, sensor and binary sensor platforms.
Last verified: 2026-11-22 (split from README.md; content not re-verified)

## Platform Configuration

### Light

**UI Configuration:**
Settings → Devices & Services → Crestron → Configure → Add Light

**YAML Configuration:**
```yaml
light:
  - platform: crestron
    name: Kitchen Light
    join: d1                    # On/off digital join
    brightness_join: a1         # Optional: brightness (0-255)
```

### Switch

**UI Configuration:**
Settings → Devices & Services → Crestron → Configure → Add Switch

**YAML Configuration:**
```yaml
switch:
  - platform: crestron
    name: Fountain Pump
    switch_join: d10
```

### Climate (Thermostat)

**UI Configuration:**
Settings → Devices & Services → Crestron → Configure → Add Climate

**YAML Configuration (Standard HVAC):**
```yaml
climate:
  - platform: crestron
    name: Living Room HVAC
    is_on_join: d20            # System on/off
    heat_sp_join: a20          # Heat setpoint (tenths, e.g., 720 = 72.0°F)
    cool_sp_join: a21          # Cool setpoint
    reg_temp_join: a22         # Current temperature
    mode_heat_join: d21        # Mode: Heat
    mode_cool_join: d22        # Mode: Cool
    mode_auto_join: d23        # Mode: Auto
    mode_off_join: d24         # Mode: Off
    fan_on_join: d25           # Fan: On
    fan_auto_join: d26         # Fan: Auto
```

**YAML Configuration (Floor Warming):**
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

### Cover (Shades/Blinds)

**UI Configuration:**
Settings → Devices & Services → Crestron → Configure → Add Cover

**YAML Configuration:**
```yaml
cover:
  - platform: crestron
    name: Living Room Shade
    join: d30                  # Open command
    is_opening_join: d31       # Optional: opening state
    is_closing_join: d32       # Optional: closing state
    is_closed_join: d33        # Optional: closed state
    stop_join: d34             # Optional: stop command
    pos_join: a30              # Optional: position (0-100)
```

### Media Player

**UI Configuration:**
Settings → Devices & Services → Crestron → Configure → Add Media Player

**YAML Configuration:**
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

### Sensor

**UI Configuration:**
Settings → Devices & Services → Crestron → Configure → Add Sensor

**YAML Configuration:**
```yaml
sensor:
  - platform: crestron
    name: Outdoor Temperature
    value_join: a50
    divisor: 10                # Optional: divide by 10 (for tenths)
    unit_of_measurement: "°F"
```

### Binary Sensor

**UI Configuration:**
Settings → Devices & Services → Crestron → Configure → Add Binary Sensor

**YAML Configuration:**
```yaml
binary_sensor:
  - platform: crestron
    name: Front Door
    join: d50
    device_class: door         # Optional: door, window, motion, etc.
```
