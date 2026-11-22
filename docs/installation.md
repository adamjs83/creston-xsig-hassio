# Installation and quick start

Covers: HACS and manual install, first setup, migrating from npope's integration (quick start).
Last verified: 2026-11-22 (split from README.md; content not re-verified)

## Installation

### HACS Installation (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three dots (⋮) → **Custom repositories**
4. Add: `https://github.com/adamjs83/creston-xsig-hassio`
5. Category: **Integration**
6. Click **Add**
7. Find **Crestron XSIG Integration** and click **Download**
8. Restart Home Assistant

### Manual Installation

1. Copy `custom_components/crestron` to your `config/custom_components/` directory
2. Restart Home Assistant

## Quick Start

### New Users

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Crestron XSIG**
3. Enter your XSIG port (default: 16384)
4. Click **Submit**
5. Use the **Configure** button to add entities

### Migrating from npope's Integration

If you're coming from the original npope integration with YAML configuration:

1. **Install this integration** (see Installation above)
2. **Keep your existing YAML** - Don't remove it yet!
3. **Restart Home Assistant**
4. **Automatic import** - Your configuration will be imported automatically
5. **Test everything** - Verify all devices work as expected
6. **Optional cleanup** - Remove `crestron:` from `configuration.yaml` and restart

**What gets imported:**
- ✅ Port configuration
- ✅ to_joins (HA → Crestron sync)
- ✅ from_joins (Crestron → HA actions)
- ✅ All settings and templates

**What stays in YAML:**
- Platform entities (lights, switches, climate, etc.)
- You can migrate these to UI configuration over time
- Both YAML and UI entities coexist peacefully
