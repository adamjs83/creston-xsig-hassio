# Crestron XSIG Home Assistant Custom Component

## Project Overview

This is a YAML-configured Home Assistant custom component for integrating Crestron control systems using the XSIG (External Signal) protocol. The component provides bidirectional communication between Home Assistant and Crestron processors through digital, analog, and serial joins.

## Project Structure

```
custom_components/crestron/
├── __init__.py           # Main component initialization & hub logic
├── manifest.json         # Component metadata
├── const.py             # Constants and configuration keys
├── crestron.py          # XSIG protocol implementation
├── light.py             # Light platform
├── switch.py            # Switch platform
├── climate.py           # Climate/HVAC platform
├── cover.py             # Cover/shade platform
├── media_player.py      # Media player platform
├── sensor.py            # Sensor platform
└── binary_sensor.py     # Binary sensor platform
```

## Configuration Method

**IMPORTANT**: This integration uses YAML configuration ONLY. There is no UI config flow.

All configuration is done in `configuration.yaml`:
- Hub configuration: `crestron:` section with port and optional to_joins/from_joins
- Platform configuration: Each platform (light, switch, etc.) configured in their respective sections

## Development Guidelines

### Code Standards
- Follow Home Assistant development guidelines
- Use async/await for all I/O operations
- Maintain YAML-only configuration (no config flow)
- Include comprehensive logging for debugging
- Write clear docstrings for all classes and methods

### Documentation Policy
**IMPORTANT:** Keep internal documentation LOCAL ONLY

**What gets pushed to git:**
- Code files in `custom_components/crestron/`
- HACS documentation: `README.md`, `info.md`, `hacs.json`
- User-facing files: `CHANGELOG.md`, `LICENSE`
- GitHub workflows: `.github/workflows/`
- Basic `.claude/project.md` and `.claude/commands/*.md` (for other contributors)

**What stays LOCAL (never pushed):**
- `ROADMAP.md` - Internal development roadmap
- `VERSIONING.md` - Internal versioning documentation
- `.claude/JOIN_PRESENCE_SPEC.md` - Technical specifications
- `.claude/commands/bump-version.md` - Internal commands
- `scripts/` - Internal automation scripts
- Working documents: `WORKING_*.md`, `NOTES_*.md`, `DRAFT_*.md`
- Scratch directories: `.claude/scratch/`, `.claude/temp/`

**Rationale:** Internal planning and development docs are for local use only. Public repository shows clean, user-focused documentation. All internal docs are in `.gitignore`.

### Testing
- Test via HACS installation in Home Assistant
- Test with actual Crestron hardware/simulator
- Verify all join types (digital, analog, serial)
- Test bidirectional communication (to_joins and from_joins)
- Test all platforms (light, switch, climate, cover, media_player, sensor, binary_sensor)

### DO NOT Change
- The YAML configuration structure - users rely on this
- The XSIG protocol implementation without thorough testing
- Join numbering or mapping logic

### Crestron XSIG Protocol
- Uses TCP socket communication
- Supports digital (d), analog (a), and serial (s) joins
- Automatic reconnection on connection loss
- Template-based state synchronization
- Script execution from join changes

## Common Tasks

Use the slash commands in `.claude/commands/` for common development tasks:
- `/review-code` - Review code for Home Assistant best practices
- `/test-validation` - Run HACS and hassfest validation
- `/update-version` - Update version and prepare release
- `/check-joins` - Review join configurations

## Release Process

1. Update version in `custom_components/crestron/manifest.json`
2. Update `CHANGELOG.md` with changes
3. Commit changes with message: `chore: bump version to X.X.X`
4. Create and push version tag: `git tag vX.X.X && git push origin vX.X.X`
5. GitHub Actions will automatically create a release
6. HACS users will be notified of the update

## Repository
- **Gitea**: https://gitea.ajsventures.us/adamjs83/crestron_custom_component.git (Primary)
- **GitHub**: Synced from Gitea
- **HACS**: Install via custom repository
- **Original Fork**: https://github.com/npope/home-assistant-crestron-component

## Credits
This is a maintained fork of @npope's original work. Always credit the original author when making changes.

## Key Files to Maintain
- `manifest.json` - Keep version updated
- `README.md` - User documentation (includes fork credits)
- `hacs.json` - HACS metadata
- `info.md` - HACS integration info
- `CHANGELOG.md` - Version history
