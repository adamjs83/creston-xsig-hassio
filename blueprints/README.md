# Crestron Integration Blueprints

This directory contains Home Assistant blueprints for the Crestron XSIG integration.

## Available Blueprints

### Crestron Dimmer/Keypad Button Controller

**File:** `automation/crestron_dimmer_button_controller.yaml`

Comprehensive automation blueprint for configuring Crestron dimmer/keypad buttons with:
- Actions for each button press type (press, double press, hold)
- Optional LED binding for visual feedback
- Support for up to 4 buttons per dimmer
- All buttons and actions are optional

## Installation

### Method 1: Import URL (Recommended)

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fadamjs83%2Fcreston-xsig-hassio%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fcrestron_dimmer_button_controller.yaml)

Or manually:
1. In Home Assistant, go to **Settings** → **Automations & Scenes** → **Blueprints**
2. Click **Import Blueprint**
3. Paste this URL:
   ```
   https://github.com/adamjs83/creston-xsig-hassio/blob/main/blueprints/automation/crestron_dimmer_button_controller.yaml
   ```
4. Click **Preview** → **Import**

### Method 2: Manual Installation

1. Copy the blueprint file to your Home Assistant configuration directory:
   ```
   config/blueprints/automation/crestron_dimmer_button_controller.yaml
   ```
2. Restart Home Assistant or reload automations
3. The blueprint will appear in **Settings** → **Automations & Scenes** → **Blueprints**

## Usage Example

### Basic Setup

1. Go to **Settings** → **Automations & Scenes**
2. Click **Create Automation** → **Use a blueprint**
3. Select **Crestron Dimmer/Keypad Button Controller**
4. Select your Crestron dimmer device
5. Configure actions for the buttons you want to use

### Example Configuration

**Button 1 - Press:** Toggle kitchen lights
```yaml
- service: light.toggle
  target:
    entity_id: light.kitchen
```

**Button 1 - Hold:** Turn off all lights in kitchen area
```yaml
- service: light.turn_off
  target:
    area_id: kitchen
```

**Button 1 - LED Binding:** Mirror kitchen light state
- Select entity: `light.kitchen`

**Button 2 - Press:** Run "Movie Mode" scene
```yaml
- service: scene.turn_on
  target:
    entity_id: scene.movie_mode
```

**Button 2 - LED Binding:** Show if TV is on
- Select entity: `media_player.living_room_tv`

### Advanced: Multi-Action Sequences

You can configure complex sequences for each button:

**Button 3 - Double Press:** Good night routine
```yaml
- service: light.turn_off
  target:
    area_id: downstairs
- service: lock.lock
  target:
    entity_id: lock.front_door
- service: alarm_control_panel.alarm_arm_night
  target:
    entity_id: alarm_control_panel.home
- service: notify.mobile_app
  data:
    message: "Good night mode activated"
```

## How LED Binding Works

When you configure LED binding for a button:
1. The LED automatically mirrors the state of the bound entity
2. Supported entity types:
   - Lights (on/off)
   - Switches (on/off)
   - Media players (playing/paused)
   - Climate (heating/cooling/idle)
   - Covers (open/closed)
   - Locks (locked/unlocked)
   - And many more!

3. The LED updates automatically whenever the bound entity changes state
4. No additional automation needed - it's handled by the integration

## Tips

- **Leave unused buttons blank** - Only configure the buttons you actually want to use
- **Test one button at a time** - Configure and test each button before moving to the next
- **Use holds for "all off"** - Common pattern: tap for single light, hold for all lights in area
- **LED binding is optional** - Use it only when you want visual feedback
- **Combine with scenes** - Button presses can trigger complex scenes with multiple actions

## Troubleshooting

**Blueprint doesn't appear:**
- Restart Home Assistant after installation
- Check that the file is in the correct directory: `config/blueprints/automation/`

**Actions don't fire:**
- Check that your dimmer is configured with the correct base join
- Verify Crestron is sending button presses (check logbook for device events)
- Ensure the button event entities show in **Developer Tools** → **States**

**LED binding doesn't work:**
- Verify the select entity exists: `select.{dimmer_name}_button_{n}_led_binding`
- Check that the bound entity name is correct
- LED binding updates may take a few seconds to take effect

## Support

For issues or questions:
- GitHub Issues: https://github.com/adamjs83/creston-xsig-hassio/issues
- Discussion: https://github.com/adamjs83/creston-xsig-hassio/discussions
