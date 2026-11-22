# Configuration

Covers: UI configuration (entity and join management) and optional YAML configuration.
Last verified: 2026-11-22 (split from README.md; content not re-verified)

## Configuration

### UI Configuration (Recommended)

After adding the integration, click **Configure** to access:

#### Entity Management

Add entities through the UI - no YAML needed:

- **Covers** - Window shades/blinds with position control
- **Binary Sensors** - Digital state monitoring (doors, motion, etc.)
- **Sensors** - Analog values with units and divisor support
- **Switches** - Simple on/off devices
- **Lights** - Lighting with optional brightness control
- **Climate** - HVAC and floor warming thermostats
- **Media Players** - AV equipment control
- **Dimmers/Keypads** - Crestron keypads with button events

#### Join Management

Configure join synchronization:

- **to_joins** - Send HA states to Crestron for feedback
- **from_joins** - Execute HA services when Crestron triggers

### YAML Configuration (Optional)

YAML configuration still works for backward compatibility:

```yaml
# Basic hub setup
crestron:
  port: 16384  # Match your XSIG symbol port

  # Sync HA states to Crestron
  to_joins:
    - join: d1
      entity_id: light.kitchen
    - join: a1
      entity_id: light.kitchen
      attribute: brightness

  # React to Crestron triggers
  from_joins:
    - join: d100
      script:
        - service: light.toggle
          target:
            entity_id: light.kitchen
```

See the **Platform Configuration** section below for YAML entity examples.
