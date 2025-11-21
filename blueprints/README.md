# Crestron Integration Blueprints

This directory contains Home Assistant blueprints for the Crestron XSIG integration.

## Available Blueprints

### Crestron Dimmer/Keypad Button Controller

**File:** `automation/crestron_dimmer_button_controller.yaml`

Comprehensive automation blueprint for configuring Crestron dimmer/keypad buttons with:
- Actions for each button press type (press, double press, hold)
- Optional LED binding for visual feedback
- Support for up to 6 buttons per dimmer
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
4. Enter your dimmer name (e.g., "Kitchen Keypad" or "TTTTEST")
5. Select the event entities for the buttons you want to use (e.g., `event.kitchen_keypad_button_1`)
6. Configure actions for each button press type
7. Optionally set LED binding to mirror entity states

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

## How LED Binding Works (v1.20.8+)

LED binding is now configured directly in the blueprint automation:

1. **Configure in Blueprint**: Select the entity you want to bind to each LED (e.g., `light.kitchen`)
2. **Automatic State Sync**: The automation monitors the bound entity and updates the LED automatically
3. **Native Entity Picker**: Use Home Assistant's built-in entity picker with search functionality
4. **Supported States**:
   - `on`, `off` - Lights, switches, fans
   - `home`, `not_home` - Person, device tracker
   - `playing`, `paused`, `idle` - Media players
   - `heat`, `cool`, `auto` - Climate
   - `open`, `closed`, `opening`, `closing` - Covers
   - `locked`, `unlocked` - Locks
   - `armed_away`, `armed_home`, `disarmed` - Alarm panels
   - And many more!

5. **Real-time Updates**: LED changes instantly when bound entity state changes

**Note:** LED binding select entities (`select.{dimmer}_button_{n}_led_binding`) were deprecated in v1.20.8. All LED binding is now handled in the blueprint.

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
- Verify the bound entity is selected in the blueprint configuration
- Check that the LED switch entity exists: `switch.{dimmer_name}_led_{n}`
- Ensure the bound entity's state is one of the supported states (on, home, playing, etc.)
- Check the automation trace in **Developer Tools** → **Traces** to see if the LED sync trigger fired

## Support

For issues or questions:
- GitHub Issues: https://github.com/adamjs83/creston-xsig-hassio/issues
- Discussion: https://github.com/adamjs83/creston-xsig-hassio/discussions
