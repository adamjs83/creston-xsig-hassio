# Dimmer and keypad configuration

Covers: Adding a dimmer/keypad, auto-sequential joins, created entities, button events, LED binding, Crestron-side programming.
Last verified: 2026-11-22 (split from README.md; content not re-verified)

## Dimmer/Keypad Configuration

Crestron keypads and dimmers are configured exclusively through the UI.

### Adding a Dimmer/Keypad

1. Go to **Settings** → **Devices & Services** → **Crestron XSIG**
2. Click **Configure**
3. Select **Add Dimmer/Keypad**
4. Choose configuration mode:
   - **Auto-Sequential** (recommended) - Specify base join, system assigns rest
   - **Manual** (advanced) - Specify each join individually

### Auto-Sequential Join Assignment

The easiest way to configure keypads. You specify one base join, and the system automatically assigns sequential joins for all buttons.

**How it works:**
- Each button uses 3 sequential digital joins (press, double-press, hold)
- LEDs use the same joins as button presses (but opposite direction)
- Optional lighting load uses a separate analog join

**Example:** 4-button keypad with base join d10
```
Button 1: d10 (press), d11 (double), d12 (hold)
Button 2: d13 (press), d14 (double), d15 (hold)
Button 3: d16 (press), d17 (double), d18 (hold)
Button 4: d19 (press), d20 (double), d21 (hold)
Lighting load: a50 (if configured)
```

**Total joins used:**
- 2 buttons = 6 joins (d10-d15)
- 3 buttons = 9 joins (d10-d18)
- 4 buttons = 12 joins (d10-d21)
- 5 buttons = 15 joins (d10-d24)
- 6 buttons = 18 joins (d10-d27)

### What Gets Created

When you add a dimmer/keypad, these entities are created automatically:

#### Event Entities (one per button)
Fire events for button actions: `press`, `double_press`, `hold`

**Event data:**
- `device_name` - Dimmer/keypad name
- `button` - Button number (1-6)
- `action` - Action type (press/double_press/hold)

#### LED Binding Selects (one per button)
Bind keypad LEDs to any HA entity for automatic feedback:
- LED mirrors bound entity state
- Supports 15+ entity types (lights, switches, locks, covers, etc.)
- Provides Crestron-style visual feedback

#### LED Switch Entities (one per button)
Manual LED on/off control:
- Direct LED control
- Can be controlled manually or by binding

#### Light Entity (if configured)
Dimmer lighting load control:
- Standard HA light entity
- On/off and brightness control
- Single analog join (0-65535)

### Handling Button Events

You have two options for responding to button presses:

#### Option 1: Switch Manager (Recommended)

[**Switch Manager**](https://github.com/Sian-Lee-SA/Home-Assistant-Switch-Manager) is a custom component that centralizes button event handling, keeping your automations organized and clutter-free.

**Why use Switch Manager:**
- ✅ Centralized configuration in one place
- ✅ Clean UI for managing all switches/keypads
- ✅ No automation clutter
- ✅ Easy to modify button actions
- ✅ Works with any event bus integration

**Installation:**

1. Install via HACS:
   - HACS → Integrations → ⋮ → Custom repositories
   - Repository: `https://github.com/Sian-Lee-SA/Home-Assistant-Switch-Manager`
   - Category: Integration
   - Install and restart

2. Create a Switch Manager blueprint for Crestron buttons:

```yaml
blueprint:
  name: Crestron Button
  service: crestron
  event_type: crestron_button_event
  buttons:
    - name: Press
      field: action
      value: press
    - name: Double Press
      field: action
      value: double_press
    - name: Hold
      field: action
      value: hold
  identifier:
    - id: button
    - id: device_name
```

3. Configure your keypads in Switch Manager UI:
   - Settings → Devices & Services → Switch Manager
   - Add Switch → Crestron Button
   - Select device and configure actions

**Example configuration in Switch Manager:**

```yaml
# Kitchen Keypad - Button 1
Device: Kitchen Keypad
Button: 1
Actions:
  Press: Turn on kitchen lights
  Double Press: Activate kitchen scene
  Hold: Turn off all kitchen devices
LED Binding: light.kitchen
```

This approach keeps all your button configurations in one place and makes them easy to modify without touching automations.

#### Option 2: Regular Automations

You can also use standard HA automations:

```yaml
automation:
  - alias: "Kitchen Button 1 Press"
    trigger:
      - platform: event
        event_type: crestron_button_event
        event_data:
          device_name: "Kitchen Keypad"
          button: 1
          action: "press"
    action:
      - service: light.toggle
        target:
          entity_id: light.kitchen

  - alias: "Kitchen Button 1 Hold"
    trigger:
      - platform: event
        event_type: crestron_button_event
        event_data:
          device_name: "Kitchen Keypad"
          button: 1
          action: "hold"
    action:
      - service: light.turn_off
        target:
          entity_id: group.kitchen_lights
```

### LED Binding for Visual Feedback

LED binding provides automatic visual feedback on your keypads - when you bind a button's LED to a HA entity, the LED automatically mirrors that entity's state.

**Example:** Kitchen keypad controlling kitchen lights
- Bind Button 1 LED to `light.kitchen`
- When `light.kitchen` turns on → LED 1 turns on
- When `light.kitchen` turns off → LED 1 turns off
- LED stays synchronized regardless of how the light was controlled (keypad, voice, automation, etc.)

**How to configure:**
1. Navigate to your dimmer/keypad device in HA
2. Find the "LED X Binding" select entity
3. Choose the entity to bind
4. LED immediately starts tracking that entity's state

**Supported bindings:**
- Lights (on/off)
- Switches (on/off)
- Locks (locked/unlocked)
- Covers (open/closed)
- Climate (heating/cooling/idle)
- Fans (on/off)
- Media Players (playing/paused)
- And more (15+ domains)

### Crestron Programming for Dimmers

In your Crestron SIMPL Windows program:

**Button Press Signals (Crestron → HA):**
```
Button 1 Press   → XSIG Digital Join d10
Button 1 Double  → XSIG Digital Join d11
Button 1 Hold    → XSIG Digital Join d12
```

**LED Feedback Signals (HA → Crestron):**
```
Button 1 LED     → XSIG Digital Join d10 (same as press join)
```

**Lighting Load (if configured):**
```
Dimmer Level (HA → Crestron) → XSIG Analog Join a50
Dimmer Feedback (Crestron → HA) → XSIG Analog Join a50 (same join)
  0 = Off
  1-65535 = On with brightness
```

**Important notes:**
- Button press and LED feedback use the **same join numbers** but are separate signals (different directions)
- Only the **press join** is used for LED feedback (not double or hold)
- Lighting load uses a **single analog join** - no separate on/off join needed
