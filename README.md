# Crestron XSIG Integration for Home Assistant

[![Version](https://img.shields.io/badge/version-1.20.9-blue.svg)](https://github.com/adamjs83/creston-xsig-hassio/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Home Assistant custom component for integrating with Crestron control systems using the XSIG (External Signal) protocol. This integration provides bidirectional communication with Crestron processors, allowing Home Assistant to control and monitor Crestron devices.

## Features

- **UI-based configuration** with automatic YAML import (v1.7.0+)
- **UI entity management** - Configure entities directly via UI (v1.8.0+)
  - Covers, binary sensors, sensors, switches, lights, climate (v1.8.0-v1.14.0)
  - Dimmers/keypads with button events and LED control (v1.17.0+)
- **Options Flow join management** - Add, edit, and remove joins via UI (v1.7.0+)
- **Bidirectional join communication** (digital, analog, and serial)
- **Multiple platform support**: lights, switches, climate, covers, media players, sensors, binary sensors, dimmers/keypads, events
- **Dimmer/Keypad support** (v1.17.0+):
  - Button press events (press, double press, hold)
  - LED binding to Home Assistant entities
  - Optional lighting load control
  - Auto-sequential or manual join assignment
  - Modern `has_entity_name` pattern for context-aware naming (v1.18.0+)
- **Pre-built automation blueprints** for easy dimmer/keypad configuration (v1.20.5+)
- **Template-based state synchronization** (Home Assistant → Crestron)
- **Script execution** from join changes (Crestron → Home Assistant)
- **Automatic reconnection** on connection loss
- **No restart required** for join/entity changes (v1.7.0+)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/adamjs83/creston-xsig-hassio`
6. Category: Integration
7. Click "Add"
8. Find "Crestron XSIG Integration" and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/crestron` directory to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

### UI Configuration (v1.7.0+)

The integration supports both UI-based setup and automatic YAML import.

#### Fresh Installation

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Crestron XSIG"
3. Enter the XSIG port number (typically 16384)
4. Click Submit
5. Use the **Configure** button to manage joins (to_joins and from_joins)

#### Automatic YAML Import (Migration from YAML)

If you have an existing YAML configuration, v1.7.0 will automatically import it on first restart:

1. Upgrade to v1.7.0
2. Restart Home Assistant
3. **Automatic import** - Your YAML configuration (port, to_joins, from_joins) will be imported
4. A notification confirms the import with counts
5. **YAML continues working** - Both configurations coexist until you remove YAML
6. **Optional**: Remove the `crestron:` section from `configuration.yaml` after testing
7. Restart HA - The dual configuration warning will disappear

**Example Import Notification:**
```
Crestron Configuration Imported ✓
Your Crestron XSIG configuration (port 16384) has been automatically imported
to the UI. You can now manage joins via the Configure button.

Imported: 47 to_joins, 2 from_joins

Your YAML configuration will continue to work. To complete the migration,
remove the 'crestron:' section from configuration.yaml and restart.
```

#### Managing Configuration via UI (Options Flow)

After setup, click the **Configure** button on your Crestron integration to:

**Join Management:**
- **Add to_join (HA→Crestron)** - Send HA state to Crestron for feedback
  - Select entity from picker
  - Specify join number (d15, a10, s5, etc.)
  - Optional: attribute, value template

- **Add from_join (Crestron→HA)** - Run HA services when Crestron triggers
  - Specify join number
  - Select service to call
  - Optional: target entity

- **Edit/Remove joins** - Modify or delete existing joins

**Entity Management (v1.8.0+):**
- **Add/Edit/Remove Covers** - Window shades/blinds with position control
- **Add/Edit/Remove Binary Sensors** - Digital state monitoring (doors, motion, etc.)
- **Add/Edit/Remove Sensors** - Analog value monitoring with units and divisor support
- **Add/Edit/Remove Switches** - Simple on/off control
- **Add/Edit/Remove Lights** - Lighting control with optional brightness
- **Add/Edit/Remove Climate** - HVAC and floor warming thermostats

**Dimmer/Keypad Management (v1.17.0+):**
- **Add Dimmer/Keypad** - Configure Crestron keypads and dimmers
  - Choose auto-sequential or manual join assignment
  - Configure 2-6 buttons with press, double press, and hold actions
  - Optional lighting load with dimming
  - Automatic creation of event entities (button presses)
  - Automatic creation of LED binding selects
  - Automatic creation of LED switch entities
- **Edit/Remove Dimmers** - Modify or delete dimmer configurations

**No restart required** - Changes take effect immediately after reload.

### YAML Configuration (Optional)

**UI configuration is recommended** for most use cases (v1.7.0+).

YAML configuration is still supported for:
- Hub setup (port configuration)
- Join synchronization (to_joins, from_joins)
- Platform entities (lights, switches, climate, etc.)
- Media players (UI entity management not yet available)

**Note:** Many entity types can now be configured via UI (v1.8.0+). YAML configuration remains optional for backward compatibility and advanced use cases.

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

#### Dimmer/Keypad (v1.17.0+)

**UI Configuration Only** - Dimmers/keypads can only be configured via the UI (no YAML support).

Use the **Configure** button → **Manage Dimmers/Keypads** to add Crestron keypads and dimmers.

**Join Assignment Modes:**

1. **Auto-Sequential (Recommended)** - Specify a base join, system auto-assigns sequentially
   - Base join d10 with 4 buttons uses d10-d21 (3 joins per button)
   - Button 1: d10 (press), d11 (double), d12 (hold)
   - Button 2: d13 (press), d14 (double), d15 (hold)
   - Button 3: d16 (press), d17 (double), d18 (hold)
   - Button 4: d19 (press), d20 (double), d21 (hold)

2. **Manual (Advanced)** - Specify each button's joins individually
   - Useful for non-sequential join assignments
   - Example: Button 1 press=d10, double=d20, hold=d30

### Auto-Sequential Join Assignment (Detailed Guide)

The auto-sequential method is the recommended approach for most installations. You specify a single base join, and the system automatically assigns sequential joins for all button functions.

#### How Auto-Sequential Works

When you configure a dimmer with auto-sequential mode, the system assigns **3 consecutive digital joins per button**:
- **Join 1**: Button press event
- **Join 2**: Button double-press event
- **Join 3**: Button hold event

**Formula:** Each button uses 3 joins starting from `base_join + (button_number - 1) * 3`

#### Join Assignment Tables by Button Count

##### 2-Button Keypad (Base join: d10)
| Button | Press | Double Press | Hold | Total Joins Used |
|--------|-------|--------------|------|------------------|
| Button 1 | d10 | d11 | d12 | d10-d15 (6 joins) |
| Button 2 | d13 | d14 | d15 | |

##### 3-Button Keypad (Base join: d10)
| Button | Press | Double Press | Hold | Total Joins Used |
|--------|-------|--------------|------|------------------|
| Button 1 | d10 | d11 | d12 | d10-d18 (9 joins) |
| Button 2 | d13 | d14 | d15 | |
| Button 3 | d16 | d17 | d18 | |

##### 4-Button Keypad (Base join: d10)
| Button | Press | Double Press | Hold | Total Joins Used |
|--------|-------|--------------|------|------------------|
| Button 1 | d10 | d11 | d12 | d10-d21 (12 joins) |
| Button 2 | d13 | d14 | d15 | |
| Button 3 | d16 | d17 | d18 | |
| Button 4 | d19 | d20 | d21 | |

##### 5-Button Keypad (Base join: d10)
| Button | Press | Double Press | Hold | Total Joins Used |
|--------|-------|--------------|------|------------------|
| Button 1 | d10 | d11 | d12 | d10-d24 (15 joins) |
| Button 2 | d13 | d14 | d15 | |
| Button 3 | d16 | d17 | d18 | |
| Button 4 | d19 | d20 | d21 | |
| Button 5 | d22 | d23 | d24 | |

##### 6-Button Keypad (Base join: d10)
| Button | Press | Double Press | Hold | Total Joins Used |
|--------|-------|--------------|------|------------------|
| Button 1 | d10 | d11 | d12 | d10-d27 (18 joins) |
| Button 2 | d13 | d14 | d15 | |
| Button 3 | d16 | d17 | d18 | |
| Button 4 | d19 | d20 | d21 | |
| Button 5 | d22 | d23 | d24 | |
| Button 6 | d25 | d26 | d27 | |

#### What Goes on Each Join

**Digital Button Joins:**

Each button join carries two types of signals:

1. **INPUT (Button Press → Home Assistant)**: Crestron sends signals TO Home Assistant
   - Press join: Pulse when button tapped once
   - Double press join: Pulse when button tapped twice quickly
   - Hold join: Signal when button pressed and held

2. **OUTPUT (LED Feedback → Crestron)**: Home Assistant sends signals TO Crestron
   - **Same join numbers** as button presses (e.g., Button 1 press uses d10 for both button input AND LED feedback output)
   - LED state controlled via LED binding or manual LED switch entity
   - Provides visual feedback on keypad

**Note:** While button press and LED feedback use the same join numbers, they are separate signals - button presses flow FROM Crestron TO Home Assistant, while LED feedback flows FROM Home Assistant TO Crestron.

**Analog Lighting Load Join (Optional):**

If you configure a lighting load (dimmer with lights):
- **Join type**: Analog (a)
- **Range**: 0-65535
  - 0 = Light off
  - 1-65535 = Light on with varying brightness
  - No separate on/off digital join needed
- **Typical join**: Usually a separate analog join (e.g., a1, a50, etc.)
- **Not part of the sequential button join range**
- **Bidirectional**: Home Assistant controls dimmer level, Crestron can send feedback

#### Step-by-Step Configuration in Home Assistant

1. **Navigate to Integration Settings**:
   - Go to Settings → Devices & Services
   - Find "Crestron XSIG Integration"
   - Click **Configure**

2. **Add Dimmer/Keypad**:
   - Select "Add Dimmer/Keypad"
   - Choose "Auto-Sequential" mode

3. **Configure Settings**:
   - **Name**: Enter friendly name (e.g., "Kitchen Keypad")
   - **Button Count**: Select 2-6 buttons
   - **Base Join**: Enter starting digital join (e.g., d10)
   - **Lighting Load** (optional):
     - Check "Include lighting load" if dimmer controls lights
     - Enter analog join (e.g., a50)

4. **Save Configuration**:
   - Click Submit
   - Entities are created automatically

#### Crestron Programming for Auto-Sequential

In your Crestron SIMPL Windows or SIMPL+ program:

**For a 4-button keypad with base join d10:**

```
Button 1:
  Press signal (to HA)    → XSIG Digital Join d10
  Double signal (to HA)   → XSIG Digital Join d11
  Hold signal (to HA)     → XSIG Digital Join d12
  LED feedback (from HA)  → XSIG Digital Join d10 (same as press)

Button 2:
  Press signal (to HA)    → XSIG Digital Join d13
  Double signal (to HA)   → XSIG Digital Join d14
  Hold signal (to HA)     → XSIG Digital Join d15
  LED feedback (from HA)  → XSIG Digital Join d13 (same as press)

Button 3:
  Press signal (to HA)    → XSIG Digital Join d16
  Double signal (to HA)   → XSIG Digital Join d17
  Hold signal (to HA)     → XSIG Digital Join d18
  LED feedback (from HA)  → XSIG Digital Join d16 (same as press)

Button 4:
  Press signal (to HA)    → XSIG Digital Join d19
  Double signal (to HA)   → XSIG Digital Join d20
  Hold signal (to HA)     → XSIG Digital Join d21
  LED feedback (from HA)  → XSIG Digital Join d19 (same as press)
```

**If dimmer has lighting load (analog join a50):**
```
Dimmer Output Level (from HA) → XSIG Analog Join a50
Dimmer Feedback (to HA)       → XSIG Analog Join a50 (same join)
  - 0 = Off
  - 1-65535 = On with brightness
```

#### Example: Complete 4-Button Dimmer Configuration

**Home Assistant Configuration:**
- **Name**: "Master Bedroom Keypad"
- **Mode**: Auto-Sequential
- **Base Join**: d100
- **Button Count**: 4
- **Lighting Load**: Yes
- **Lighting Load Join**: a25

**Join Assignment:**
| Function | Join | Direction | Purpose |
|----------|------|-----------|---------|
| Button 1 Press | d100 | Crestron → HA | Button press detection |
| Button 1 LED | d100 | HA → Crestron | LED feedback (same join) |
| Button 1 Double | d101 | Crestron → HA | Double press detection |
| Button 1 Hold | d102 | Crestron → HA | Hold detection |
| Button 2 Press | d103 | Crestron → HA | Button press detection |
| Button 2 LED | d103 | HA → Crestron | LED feedback (same join) |
| Button 2 Double | d104 | Crestron → HA | Double press detection |
| Button 2 Hold | d105 | Crestron → HA | Hold detection |
| Button 3 Press | d106 | Crestron → HA | Button press detection |
| Button 3 LED | d106 | HA → Crestron | LED feedback (same join) |
| Button 3 Double | d107 | Crestron → HA | Double press detection |
| Button 3 Hold | d108 | Crestron → HA | Hold detection |
| Button 4 Press | d109 | Crestron → HA | Button press detection |
| Button 4 LED | d109 | HA → Crestron | LED feedback (same join) |
| Button 4 Double | d110 | Crestron → HA | Double press detection |
| Button 4 Hold | d111 | Crestron → HA | Hold detection |
| Lighting Load | a25 | Both | Dimmer level (0-65535) |

**Entities Created in Home Assistant:**
- `event.master_bedroom_keypad_button_1` (fires press/double_press/hold events)
- `event.master_bedroom_keypad_button_2`
- `event.master_bedroom_keypad_button_3`
- `event.master_bedroom_keypad_button_4`
- `select.master_bedroom_keypad_led_1_binding` (bind LED to HA entity)
- `select.master_bedroom_keypad_led_2_binding`
- `select.master_bedroom_keypad_led_3_binding`
- `select.master_bedroom_keypad_led_4_binding`
- `switch.master_bedroom_keypad_led_1` (manual LED control)
- `switch.master_bedroom_keypad_led_2`
- `switch.master_bedroom_keypad_led_3`
- `switch.master_bedroom_keypad_led_4`
- `light.master_bedroom_keypad_light` (dimmer lighting load)

#### Choosing a Base Join

**Best Practices:**
- Choose a base join that doesn't conflict with other entities
- Leave room for expansion (e.g., if you have 4 buttons but might add more keypads, plan accordingly)
- Common ranges:
  - d10-d50: Small systems
  - d100-d200: Medium systems (easier to remember/organize)
  - d500+: Large systems with many devices

**Example Join Planning:**
- Keypad 1 (Kitchen, 4 buttons): d10-d21 (12 joins)
- Keypad 2 (Living Room, 6 buttons): d25-d42 (18 joins)
- Keypad 3 (Master Bedroom, 4 buttons): d50-d61 (12 joins)

**Configuration Options:**
- **Name** - Friendly name for the dimmer/keypad
- **Button Count** - 2 to 6 buttons
- **Lighting Load** (optional) - Control a dimmer's lighting load
  - Brightness join (analog, 0-65535) - Controls both on/off and brightness level

**Entities Created Automatically:**

Each dimmer/keypad creates the following entities grouped under one device:

1. **Event Entities** (one per button) - Fire events for button actions:
   - Event types: `press`, `double_press`, `hold`
   - Event data includes: `button`, `action`, `device_name`
   - Use in automations with event triggers

2. **LED Binding Selects** (one per button) - Bind LEDs to HA entities for feedback:
   - Dropdown of all bindable entities (lights, switches, locks, covers, etc.)
   - LED automatically mirrors bound entity state (Crestron feedback)
   - Provides visual feedback of device status on keypad
   - Supports 15+ domains with 30+ state mappings

3. **LED Switch Entities** (one per button) - Direct LED control:
   - Manual LED on/off control
   - Uses button press join for LED OUTPUT (HA → Crestron)
   - Can be controlled by LED binding or manually

4. **Light Entity** (if lighting load configured) - Dimmer light control:
   - On/off and brightness control
   - Standard Home Assistant light entity

**Example Automation using Button Events:**

```yaml
automation:
  - alias: "Kitchen Keypad Button 1 Double Press"
    trigger:
      - platform: event
        event_type: crestron_button_event
        event_data:
          device_name: "Kitchen Keypad"
          button: 1
          action: "double_press"
    action:
      - service: scene.turn_on
        target:
          entity_id: scene.kitchen_evening
```

**LED Binding for Feedback:**

In Crestron systems, keypad LEDs provide visual feedback of controlled device status. The LED binding feature automatically synchronizes LED state with Home Assistant entities.

**Example:** Kitchen Keypad controlling kitchen lights
- Bind Button 1 LED to `light.kitchen` entity
- When `light.kitchen` turns on (via HA, voice, or keypad) → LED 1 turns on
- When `light.kitchen` turns off → LED 1 turns off
- LED stays synchronized regardless of how the light was controlled

This provides the same feedback behavior as traditional Crestron programming, but managed automatically by Home Assistant.

**How to configure:**
1. Navigate to the dimmer/keypad device in Home Assistant
2. Find the "LED X Binding" select entity
3. Choose the entity to bind (light, switch, lock, cover, etc.)
4. LED will immediately start tracking that entity's state

**Supported entity types for binding:**
- Lights (on/off state)
- Switches (on/off state)
- Locks (locked/unlocked state)
- Covers (open/closed state)
- Climate (heating/cooling/idle state)
- Fans (on/off state)
- Media players (playing/paused state)
- And many more (15+ domains supported)

**Crestron Programming for Dimmers/Keypads:**

In your Crestron program:
1. Wire button press signals to digital joins (press, double press, hold)
   - These are INPUT signals: Crestron → Home Assistant
2. Wire LED feedback signals to the **same digital joins**
   - These are OUTPUT signals: Home Assistant → Crestron
   - Example: Button 1 press uses d10 for button press INPUT and d10 for LED feedback OUTPUT
   - Same join number, but separate signal directions
   - Allows Home Assistant to both detect button presses and control LED state
3. If using lighting load: wire dimmer control to a single analog join (0-65535)
   - Home Assistant sends dimmer level to Crestron (OUTPUT: HA → Crestron)
   - Crestron can send feedback to Home Assistant (INPUT: Crestron → HA)
   - Value 0 = off, values 1-65535 = on with varying brightness
   - No separate digital on/off join is needed

**Important:**
- Button press joins and LED feedback use the same join numbers but are separate signals (one input, one output)
- Lighting load uses a single analog join for full dimmer control
- Only the press join is used for LED feedback, not double press or hold joins

### Modern Entity Naming (v1.18.0+)

Dimmer/keypad entities use Home Assistant's modern `has_entity_name = True` pattern for cleaner, context-aware naming.

**How it works:**

Home Assistant automatically combines device name + entity name:
- **Device:** "Kitchen Keypad" (configured dimmer name)
- **Entity:** "Button 1" (feature identifier)
- **Result:** "Kitchen Keypad Button 1" (friendly name)

**Context-aware display:**

Entity names appear differently depending on where you view them:

1. **Within Device Page** (Settings → Devices → Your Dimmer):
   - Shows: "Light", "Button 1", "LED 1 Binding"
   - Why: Device name is already shown at the top, no redundancy needed

2. **Dashboards, Automations, Entity Lists**:
   - Shows: "Kitchen Keypad Light", "Kitchen Keypad Button 1"
   - Why: Full context needed when device name isn't displayed

3. **Entity Attributes** (Developer Tools → States):
   - `friendly_name`: "Kitchen Keypad Button 1" (full name stored)

**Example entity names for a dimmer named "Kitchen Keypad":**

| Entity Type | Entity Name | Friendly Name (Full) | Display in Device Page |
|-------------|-------------|---------------------|----------------------|
| Event | "Button 1" | "Kitchen Keypad Button 1" | "Button 1" |
| Event | "Button 2" | "Kitchen Keypad Button 2" | "Button 2" |
| Select | "LED 1 Binding" | "Kitchen Keypad LED 1 Binding" | "LED 1 Binding" |
| Select | "LED 2 Binding" | "Kitchen Keypad LED 2 Binding" | "LED 2 Binding" |
| Switch | "LED 1" | "Kitchen Keypad LED 1" | "LED 1" |
| Switch | "LED 2" | "Kitchen Keypad LED 2" | "LED 2" |
| Light | "Light" | "Kitchen Keypad Light" | "Light" |

**Benefits:**
- ✅ Future-proof (mandatory for new integrations per HA standards)
- ✅ Automatic updates when device is renamed
- ✅ Cleaner code without name duplication
- ✅ Matches modern integrations (Z-Wave, Zigbee, Matter, etc.)

**Note:** Only dimmer-related entities use this pattern. Standalone switches, lights, covers, etc. continue to use full names as configured.

## Blueprints

Pre-built automation blueprints make it easy to configure your Crestron dimmers/keypads without writing YAML.

### Dimmer/Keypad Button Controller Blueprint

[![Open your Home Assistant instance and show the blueprint import dialog.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fadamjs83%2Fcreston-xsig-hassio%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fcrestron_dimmer_button_controller.yaml)

**Features:**
- Configure actions for button presses (press, double press, hold)
- Set LED binding for visual feedback
- Support for up to 6 buttons per dimmer
- All buttons and actions are optional

**Quick Start:**
1. Click the badge above to import the blueprint
2. Go to **Settings** → **Automations & Scenes** → **Create Automation** → **Use a blueprint**
3. Select **Crestron Dimmer/Keypad Button Controller**
4. Enter your dimmer name
5. Select the event entities for the buttons you want to use
6. Configure actions for each button press type

**Example Use Cases:**
- Button 1 Press: Toggle kitchen lights
- Button 1 Hold: Turn off all kitchen lights
- Button 2 Press: Activate "Movie Mode" scene
- Button 2 LED Binding: Show TV state (on/off)

**Full Documentation:** See [blueprints/README.md](./blueprints/README.md) for detailed usage instructions and examples.

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

## Roadmap

### Current Status (v1.18.0)

**Fully Implemented:**
- ✅ UI-based configuration with Config Flow
- ✅ UI join management (to_joins, from_joins)
- ✅ UI entity management for: Covers, Binary Sensors, Sensors, Switches, Lights, Climate
- ✅ UI dimmer/keypad management with button events and LED control
- ✅ Modern `has_entity_name = True` pattern for dimmer entities
- ✅ Automatic YAML import
- ✅ Multiple platform support (8 platforms)
- ✅ Template-based state synchronization
- ✅ Script execution from join changes
- ✅ Auto-sequential and manual join assignment for dimmers
- ✅ LED binding with 15+ supported domains

### Planned Features

**High Priority:**
- 🔄 UI entity management for Media Players
- 🔄 Extend modern `has_entity_name` pattern to other entity types (covers, climate, etc.)
- 🔄 Entity naming consistency review across all platforms

**Medium Priority:**
- 📋 Scene support - Trigger Crestron scenes from HA
- 📋 Number entities - For analog value sliders
- 📋 Enhanced diagnostics and troubleshooting tools
- 📋 Connection status sensor

**Low Priority / Future Consideration:**
- 💡 Translation support for entity names
- 💡 Custom device icons for dimmers/keypads
- 💡 Bulk operations for join management
- 💡 Join conflict detection and warnings

**Not Planned:**
- ❌ YAML configuration for dimmers/keypads (UI-only by design)
- ❌ Bidirectional serial join support (technical limitations)

### Completed Milestones

- ✅ **v1.18.0** - Modern entity naming pattern
- ✅ **v1.17.x** - Complete dimmer/keypad support
- ✅ **v1.8.0-v1.14.0** - UI entity management for 6 platforms
- ✅ **v1.7.0** - UI join management and YAML import
- ✅ **v1.6.0** - Config Flow implementation

### Version Philosophy

- **Major versions (2.0.0)**: Breaking changes, architecture updates
- **Minor versions (1.x.0)**: New features, new entity types, new platforms
- **Patch versions (1.x.x)**: Bug fixes, improvements, minor enhancements

We follow [Semantic Versioning](https://semver.org/) and maintain backward compatibility whenever possible.

## Credits

This component is forked from the excellent work by [@npope](https://github.com/npope) - [home-assistant-crestron-component](https://github.com/npope/home-assistant-crestron-component)

### Enhancements in this fork:
- **v1.18.0**: Modern entity naming with `has_entity_name = True` pattern for dimmer entities
- **v1.17.0**: Complete dimmer/keypad support with button events and LED control
- **v1.17.1**: Manual join assignment mode for flexible keypad configuration
- **v1.17.2**: Automatic device and entity cleanup on dimmer removal
- **v1.8.0-v1.14.0**: UI entity management for covers, binary sensors, sensors, switches, lights, climate
- **v1.7.0**: UI-based join management with Options Flow
- **v1.7.0**: Automatic YAML import for seamless migration
- **v1.6.0**: UI-based configuration with Config Flow
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
