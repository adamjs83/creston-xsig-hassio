# Migration guide

Covers: Migrating from npope's original integration and from YAML to UI configuration.
Last verified: 2026-11-22 (split from README.md; content not re-verified)

## Migration Guide

### From npope's Original Integration

**Step 1: Install this integration**
- Install via HACS or manually (see Installation above)
- Don't remove your existing YAML configuration yet

**Step 2: Restart and verify import**
- Restart Home Assistant
- Check for import notification
- Verify all entities still work

**Step 3: Understand what was imported**
- Port configuration → UI config entry
- to_joins → UI join management
- from_joins → UI join management
- Platform entities → Still in YAML (migrate over time)

**Step 4: Optional cleanup**
- Test everything thoroughly first
- Remove `crestron:` section from `configuration.yaml`
- Restart Home Assistant
- Dual config warning will disappear

**Step 5: Migrate platform entities (optional)**
- Platform entities can stay in YAML indefinitely
- Or migrate them to UI configuration one by one
- Both YAML and UI entities work together

### From YAML to UI Configuration

You can migrate entities from YAML to UI at your own pace:

**YAML Light:**
```yaml
light:
  - platform: crestron
    name: Kitchen Light
    join: d1
    brightness_join: a1
```

**UI Migration:**
1. Settings → Devices & Services → Crestron → Configure
2. Select "Add Light"
3. Enter name, joins
4. Click Submit
5. Remove from YAML and restart

Both configurations can coexist - migrate when convenient.
