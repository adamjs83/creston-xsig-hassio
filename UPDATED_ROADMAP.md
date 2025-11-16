# Updated Crestron Integration Roadmap

**Version:** 2.1 (Architectural Focus)
**Date:** 2025-11-16 (Updated)
**Original Date:** 2025-11-11
**Current Version:** v1.5.5
**Strategy:** Architecture-first, incremental releases, zero rework

---

## Executive Summary

- **Current state:** v1.5.5 - Foundation complete, ready for config flow
- **Completed releases:** v1.4.0, v1.5.0-v1.5.5 (Phase 1 complete!)
- **Remaining releases:** 5 micro-releases (v1.6.0-v1.8.0, v1.10.0-v1.11.0)
- **Estimated timeline:** 8-10 weeks (conservative)
- **Key architectural decision:** Device registry → Platform loading → Config flow (✅ First two done!)

**Critical Success Factor:** We already have the foundation (unique IDs + RestoreEntity). Now we modernize the architecture without breaking what works.

---

## Recent Progress (Since Original Roadmap)

**✅ COMPLETED (2025-11-11):**

1. **v1.4.0 - Device Registry Integration** ✅
   - Added device_info to all 7 platforms
   - Device appears in UI under Settings → Devices
   - Foundation for config entries complete

2. **v1.5.0 - Platform Loading Modernization** ✅
   - Replaced deprecated async_load_platform
   - Uses modern asyncio.gather pattern
   - No more deprecation warnings

3. **v1.5.1 - Port Attribute Fix** ✅
   - Fixed CrestronXsig.port attribute
   - Device identifiers now work correctly

4. **v1.5.2-v1.5.5 - Cover Stop Bug Fixed** ✅
   - Fixed async event loop errors
   - Proper digital signal transmission
   - Cleared analog state after stop
   - **BONUS:** v1.9.0 no longer needed!

**🎯 NEXT UP: v1.6.0 - Config Flow Hub Setup**
- Detailed implementation plan ready
- All prerequisites met
- Target: UI-based hub configuration

---

## Lessons Applied from v1.2.0 Failures

### What We're Doing Differently

1. **ONE change per release** - No bundling of unrelated features
2. **Architecture before features** - Changes that enable future work come first
3. **Test between releases** - Minimum 2-3 day validation per release
4. **No premature optimization** - Only fix what's broken or deprecated

### What We Learned

- ✅ RestoreEntity is DONE and WORKING - don't touch it
- ✅ Unique IDs are stable - leave them alone
- ✅ Join tracking works - no changes needed
- ✅ Cover stop bug FIXED (v1.5.2-v1.5.5)
- ⚠️ Small optimization opportunity (sync_joins) but not critical
- ✅ Deprecated patterns FIXED (v1.5.0)

---

## Architectural Priorities

### Priority 1: Foundation Changes (Must Do First)

**These changes MUST happen before config flow because config flow architecture requires them.**

1. **Device Registry Integration** (v1.4.0)
   - **Why now:** Config flow creates config entries, which expect device_info
   - **Enables:** Proper device grouping in UI, foundation for config flow
   - **Rework risk:** HIGH if done after config flow (would require changing entry setup)

2. **Fix Deprecated Platform Loading** (v1.5.0)
   - **Why now:** `async_load_platform` will break in HA 2025.x
   - **Enables:** Modern platform setup pattern needed for config flow
   - **Rework risk:** HIGH if done with config flow (too many changes at once)

### Priority 2: Feature Implementation

**These build on the foundation and can be done incrementally.**

3. **Config Flow - Phase 1: Hub Setup** (v1.6.0)
   - **Why now:** After device registry and platform loading fixed
   - **Enables:** UI configuration of hub port
   - **Rework risk:** MEDIUM if entity config changes later

4. **Config Flow - Phase 2: YAML Import** (v1.7.0)
   - **Why now:** Immediately after hub setup works
   - **Enables:** Migration path for existing users
   - **Rework risk:** LOW - migration is one-time code

5. **Entity Categories** (v1.8.0)
   - **Why now:** After config flow stabilizes
   - **Enables:** Better UI organization (diagnostic sensors, etc.)
   - **Rework risk:** NONE - purely additive

### Priority 3: Polish & Bug Fixes

**Nice-to-haves that don't cause rework and fix known issues.**

6. **~~Fix Cover Stop Bug~~** (~~v1.9.0~~) ✅ **ALREADY FIXED IN v1.5.2-v1.5.5**
   - **Status:** COMPLETE - No longer needed as separate release
   - **Fixed:** Async event loop errors, signal transmission, state clearing

7. **Optimize Sync Callback** (v1.10.0)
   - **Why now:** After config flow proven stable
   - **Enables:** Better performance, cleaner logs
   - **Rework risk:** NONE

8. **Add Type Hints** (v1.11.0)
   - **Why now:** Code quality improvement, no functional changes
   - **Enables:** Better IDE support, easier maintenance
   - **Rework risk:** NONE

---

## Detailed Release Plan

### Phase 1: Architecture Foundation (v1.4.0 - v1.5.0) ✅ COMPLETE

**Goal:** Modernize base architecture to support config flow

**Status:** ✅ **COMPLETED** (2025-11-11)

---

#### v1.4.0: Device Registry Integration ✅ COMPLETE

**What:** Add `device_info` property to all entity classes, creating a single Crestron device per hub.

**Why Now:** Config flow expects entities to have device associations. Doing this after config flow would require modifying the config entry setup logic.

**Risk:** LOW
**Complexity:** 2-3 hours coding, 3-4 days testing
**Lines Changed:** ~100 (add device_info to 7 platform files + __init__.py changes)

**Success Criteria:**
- [ ] Single "Crestron Control System" device appears in device registry
- [ ] All entities linked to this device
- [ ] Device page shows all Crestron entities
- [ ] No impact on existing functionality
- [ ] Entities still restore state correctly

**Enables:**
- Config flow device creation
- Proper entity grouping in UI
- Device-level diagnostics

**Rework Risk:** If done after config flow, would need to modify:
- Config entry creation logic
- Device identifier strategy
- Migration code for existing entities

**Implementation Notes:**
```python
# In each platform file
@property
def device_info(self):
    """Return device info for this entity."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"crestron_{self._hub.port}")},
        name="Crestron Control System",
        manufacturer="Crestron Electronics",
        model="XSIG Gateway",
        sw_version="1.4.0",
    )
```

**Testing Focus:**
- Install fresh, verify device created
- Upgrade from v1.3.0, verify device created
- Verify all 7 platforms create entities under same device
- Check device page in UI shows entity list

---

#### v1.5.0: Migrate from async_load_platform to Modern Setup ✅ COMPLETE

**What:** Replace deprecated `async_load_platform` with proper platform forwarding, preparing for config entries.

**Why Now:**
- `async_load_platform` is deprecated and will be removed
- Config flow requires `async_forward_entry_setups`
- Doing this with config flow = too many changes at once

**Risk:** MEDIUM (changes core setup flow)
**Complexity:** 3-4 hours coding, 4-5 days testing
**Lines Changed:** ~150 (__init__.py refactor + all platform files)

**Success Criteria:**
- [ ] All platforms load via new setup method
- [ ] No deprecation warnings in logs
- [ ] All entities still work correctly
- [ ] State restoration unchanged
- [ ] Device registry integration intact

**Enables:**
- Foundation for config entries
- Modern Home Assistant patterns
- Future-proof against HA breaking changes

**Rework Risk:** If done with config flow simultaneously:
- Can't isolate which change broke what
- Setup errors harder to debug
- Migration path becomes complex

**Implementation Notes:**
```python
# In __init__.py
async def async_setup(hass, config):
    """Set up the crestron component."""
    if config.get(DOMAIN) is not None:
        hass.data[DOMAIN] = {}
        hub = CrestronHub(hass, config[DOMAIN])
        await hub.start()

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, hub.stop)

        # NEW: Forward to platforms properly
        for platform in PLATFORMS:
            hass.async_create_task(
                hass.helpers.discovery.async_load_platform(
                    platform, DOMAIN, {}, config
                )
            )
    return True
```

**Testing Focus:**
- All 7 platforms load successfully
- Check startup logs for deprecation warnings
- Test with multiple entities per platform
- Verify no regressions in functionality

---

### Phase 2: Config Flow Implementation (v1.6.0 - v1.7.0)

**Goal:** Add UI configuration while maintaining YAML compatibility

---

#### v1.6.0: Config Flow - Hub Setup

**What:** Implement basic config flow for hub port configuration.

**Why Now:** After device registry and platform loading are modernized.

**Risk:** MEDIUM-HIGH (new feature, changes initialization)
**Complexity:** 6-8 hours coding, 5-7 days testing
**Lines Changed:** ~300 (new config_flow.py, strings.json, translations/, __init__.py changes)

**Success Criteria:**
- [ ] Can add integration via UI
- [ ] Port validation works
- [ ] Hub connects successfully
- [ ] Entities still configured via YAML (for now)
- [ ] Device created automatically
- [ ] No duplicate setups allowed

**Enables:**
- UI-based integration setup
- Better user experience for new installs
- Foundation for entity options flow (future)

**Rework Risk:** LOW - Entity configuration stays YAML for now

**Files to Create:**
- `config_flow.py` (~200 lines)
- `strings.json` (~30 lines)
- `translations/en.json` (~30 lines)

**Files to Modify:**
- `__init__.py` (add async_setup_entry, async_unload_entry)
- `manifest.json` (update config_flow flag)

**Implementation Strategy:**

1. Create config flow with single step (port input)
2. Validate port is not in use
3. Create config entry
4. Set up hub in async_setup_entry
5. Keep YAML loading for backward compatibility

**Testing Focus:**
- Fresh install via UI only
- Fresh install via YAML only (should still work)
- Multiple instances (different ports)
- Port conflict detection
- Entry reload functionality

---

#### v1.7.0: Config Flow - YAML Import

**What:** Automatic migration from YAML configuration to config entries.

**Why Now:** Immediately after basic config flow works, while fresh in mind.

**Risk:** MEDIUM (migration code is tricky)
**Complexity:** 3-4 hours coding, 4-5 days testing
**Lines Changed:** ~100 (config_flow.py additions, __init__.py changes)

**Success Criteria:**
- [ ] YAML config automatically imported on startup
- [ ] Config entry created with YAML settings
- [ ] YAML can be removed (integration continues working)
- [ ] No duplicate entries on multiple restarts
- [ ] Migration logged clearly for users

**Enables:**
- Smooth upgrade path for existing users
- Deprecation of YAML configuration
- Single source of truth (config entries)

**Rework Risk:** NONE - Migration is one-time code

**Implementation Notes:**
```python
# In config_flow.py
async def async_step_import(self, import_config):
    """Import configuration from YAML."""
    return await self.async_step_user(import_config)

# In __init__.py async_setup
if config.get(DOMAIN) is not None:
    # Trigger import flow
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config[DOMAIN]
        )
    )
```

**Testing Focus:**
- Upgrade from v1.6.0 with YAML config
- Verify entry created automatically
- Remove YAML, restart, verify still works
- Check for duplicate entries on multiple restarts
- Verify entity configurations preserved

---

### Phase 3: Polish & Enhancement (v1.8.0 - v1.11.0)

**Goal:** Improve user experience and code quality

---

#### v1.8.0: Entity Categories

**What:** Add entity categories (diagnostic, config) to appropriate entities.

**Why Now:** After config flow stabilizes, this is pure UI polish.

**Risk:** LOW
**Complexity:** 1-2 hours coding, 2-3 days testing
**Lines Changed:** ~50 (add entity_category to sensors, binary_sensors)

**Success Criteria:**
- [ ] Diagnostic sensors properly categorized
- [ ] Config entities properly categorized
- [ ] Entities appear in correct UI sections
- [ ] No functional changes

**Enables:**
- Better UI organization
- Hidden diagnostic entities by default
- Follows HA best practices

**Rework Risk:** NONE - purely additive

**Implementation:**
```python
# In sensor.py for diagnostic sensors
@property
def entity_category(self):
    """Return the entity category."""
    return EntityCategory.DIAGNOSTIC
```

**Categorization Strategy:**
- **Diagnostic:** Temperature feedback joins, status joins
- **Config:** Configuration-related entities (if any)
- **None:** User-facing controls (lights, switches, etc.)

**Testing Focus:**
- Check UI shows correct categories
- Verify diagnostic entities hidden by default
- Confirm no functionality changes

---

#### ~~v1.9.0: Fix Cover Stop Bug~~ ✅ ALREADY COMPLETE (v1.5.2-v1.5.5)

**Status:** ✅ **FIXED IN v1.5.2-v1.5.5** - This release is no longer needed!

**What Was Fixed:** The `async_stop_cover` callback and state management issues.

**Completed Changes:**
- v1.5.2: Fixed event loop error (use asyncio.sleep)
- v1.5.3: Additional async fixes
- v1.5.4: Ensure digital signals transmitted
- v1.5.5: Clear analog state after stop to allow direction changes

**Success Criteria:**
- [x] Cover stop command works correctly
- [x] No errors in logs
- [x] Stop pulse properly times out
- [x] Direction changes work after stop

**Result:**
- ✅ Proper cover stop functionality working
- ✅ Cleaner code
- ✅ Bug fixed ahead of schedule!
- ✅ No separate release needed

---

#### v1.10.0: Optimize sync_joins_to_hub

**What:** Improve the sync callback to only send initialized values, add better logging.

**Why Now:** After config flow proven stable, safe to optimize.

**Risk:** LOW
**Complexity:** 2 hours coding, 3-4 days testing
**Lines Changed:** ~30 (__init__.py sync method)

**Success Criteria:**
- [ ] Sync only sends valid template values
- [ ] No zeros sent on restart
- [ ] Debug logging minimal but informative
- [ ] No regressions in to_joins functionality

**Enables:**
- Better startup behavior
- Cleaner logs
- More reliable Crestron sync

**Rework Risk:** NONE

**Current Issue:**
```python
# Lines 200-234 already check for "None" but could be cleaner
```

**Optimization:**
```python
async def sync_joins_to_hub(self):
    """Sync join values from HA to Crestron (only valid values)."""
    synced_count = 0
    for join, template in self.to_hub.items():
        result = template.async_render()

        # Skip None/unavailable/unknown values
        if result in ("None", "unavailable", "unknown", None):
            continue

        # ... existing logic ...
        synced_count += 1

    _LOGGER.info(f"Synced {synced_count}/{len(self.to_hub)} joins to Crestron")
```

**Testing Focus:**
- Restart HA, check sync behavior
- Verify no invalid values sent
- Check log output is reasonable
- Test to_joins functionality

---

#### v1.11.0: Add Type Hints Throughout

**What:** Add comprehensive type hints to all files.

**Why Now:** Code quality improvement, no functional changes.

**Risk:** VERY LOW
**Complexity:** 4-6 hours coding, 2-3 days testing
**Lines Changed:** ~500 (all files)

**Success Criteria:**
- [ ] mypy passes with no errors
- [ ] Type hints on all functions and methods
- [ ] No functional changes
- [ ] Better IDE autocomplete

**Enables:**
- Easier maintenance
- Better IDE support
- Catch potential bugs early
- Professional code quality

**Rework Risk:** NONE

**Implementation:**
```python
from typing import Any, Callable, Dict, Optional, Set
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry
) -> bool:
    """Set up Crestron from a config entry."""
    # ...
```

**Testing Focus:**
- Run mypy on all files
- Verify no runtime changes
- Test all platforms still work

---

## Deferred Features

### Not in Scope for v1.x

These features are deferred to v2.0+ (major version):

1. **Entity Options Flow** (UI-based entity configuration)
   - **Why deferred:** YAML entity config works well, complex UI needed
   - **Complexity:** Very high
   - **Risk:** Breaking change for users
   - **Timeline:** 6+ months development

2. **Data Coordinator Pattern**
   - **Why deferred:** Current callback system works fine
   - **Complexity:** Major refactor
   - **Benefit:** Optimization, not critical
   - **Timeline:** 3+ months development

3. **Multiple Hub Support**
   - **Why deferred:** Rare use case, config flow makes it possible but not urgent
   - **Complexity:** Medium
   - **Current workaround:** Users can install integration multiple times
   - **Timeline:** 2+ months development

4. **Auto-Discovery**
   - **Why deferred:** XSIG doesn't support discovery protocol
   - **Complexity:** Would require Crestron cooperation
   - **Feasibility:** Low

5. **Advanced Diagnostics Panel**
   - **Why deferred:** Nice-to-have, not critical
   - **Complexity:** Medium
   - **Current workaround:** Logs show everything needed
   - **Timeline:** 1+ month development

---

## Migration Path

### From v1.3.0 to v1.4.0 (Device Registry)
**User Impact:** None visible
**Action Required:** None - automatic upgrade
**Breaking Changes:** None
**Rollback:** Safe - just downgrade via HACS

### From v1.4.0 to v1.5.0 (Platform Loading)
**User Impact:** None visible
**Action Required:** None - automatic upgrade
**Breaking Changes:** None
**Rollback:** Safe - just downgrade via HACS

### From v1.5.0 to v1.6.0 (Config Flow)
**User Impact:** Integration appears in UI integrations page
**Action Required:** None - YAML still works
**Breaking Changes:** None
**Rollback:** Safe - YAML config preserved

### From v1.6.0 to v1.7.0 (YAML Import)
**User Impact:** YAML config migrated to config entry automatically
**Action Required:** Can remove YAML config after migration (optional)
**Breaking Changes:** None
**Rollback:** Safe - can re-add YAML config if needed

**Migration Notification Template:**
```yaml
# Example persistent notification shown to user
title: "Crestron Integration Migrated"
message: |
  Your Crestron XSIG configuration has been automatically migrated
  to a config entry. You can now safely remove the YAML configuration
  from configuration.yaml.

  The integration will continue to work exactly as before.
```

### From v1.7.0 to v1.11.0
**User Impact:** Gradual improvements, no disruption
**Action Required:** None
**Breaking Changes:** None
**Rollback:** Safe at any point

---

## Critical Decisions

### Decision 1: Device Registry Before Config Flow

**Options:**
- **Option A:** Do device registry first (RECOMMENDED)
- **Option B:** Do config flow first, add device registry later

**Recommendation:** Option A

**Rationale:**
- Config flow creates config entries, which should have device info
- Doing device registry after config flow requires modifying entry creation
- Device registry is simpler to test in isolation
- HA best practice: devices should exist before entities

**Trade-offs:**
- Adds one extra release (v1.4.0)
- Users see device grouping earlier (benefit)
- Cleaner architecture

---

### Decision 2: YAML Import Timing

**Options:**
- **Option A:** Import in same release as basic config flow (v1.6.0)
- **Option B:** Import in separate release (v1.7.0) - RECOMMENDED

**Recommendation:** Option B

**Rationale:**
- Basic config flow needs to be proven stable first
- Migration code adds complexity and testing burden
- Separating allows focused testing of each feature
- Follows "one feature per release" policy

**Trade-offs:**
- One extra release
- Users on YAML wait one more release for migration
- But safer and more testable

---

### Decision 3: Entity Configuration Strategy

**Options:**
- **Option A:** Keep YAML entity config forever
- **Option B:** Build entity options flow (deferred to v2.0)
- **Option C:** Hybrid: YAML for power users, UI for simple cases

**Recommendation:** Option A for v1.x, Option B for v2.0+

**Rationale:**
- YAML works well for Crestron's join-based model
- Entity options flow is complex (need UI for join configuration)
- No user complaints about YAML entity config
- Config flow for hub is enough for v1.x

**Trade-offs:**
- Not fully UI-configurable (but acceptable)
- Advanced users prefer YAML anyway
- Can revisit in v2.0 based on user feedback

---

### Decision 4: Unique ID Format Stability

**Decision:** Keep existing format: `crestron_{platform}_{join_type}{join_number}`

**Rationale:**
- Already deployed in v1.3.0
- Stable and predictable
- Changing would orphan existing entities
- Format works well

**Alternative Considered:** UUID-based, but less human-readable

---

### Decision 5: RestoreEntity - Already Implemented!

**Decision:** Leave RestoreEntity as-is in v1.3.0

**Rationale:**
- Already fully implemented and working
- Follows best practices (real data → restored → default)
- Proper validation in place
- No issues reported
- **DO NOT TOUCH** - it works!

**Historical Note:** Original roadmap planned RestoreEntity for Phase 1, but it's already done. This roadmap focuses on what's actually missing.

---

## Comparison to Original Plans

### What Changed from ROADMAP.md

**Original Plan Issues:**
1. ❌ Assumed RestoreEntity not done (it IS done in v1.3.0)
2. ❌ Planned to fix "reboot dip" (already fixed)
3. ❌ Planned join validity tracking (already implemented)
4. ❌ Suggested big-bang config flow (we're doing incremental)
5. ❌ Planned config flow before device registry (wrong order)

**New Plan Fixes:**
1. ✅ Recognizes v1.3.0 current state accurately
2. ✅ Focuses on what's actually missing
3. ✅ Correct architectural ordering (device → platform → config flow)
4. ✅ Smaller, more testable releases
5. ✅ Clear dependencies between features

### What Changed from RESTORE_ENTITY_PLAN.md

**Why This Plan is Different:**
- RestoreEntity plan assumed it needed implementing
- RestoreEntity is DONE in v1.3.0
- This roadmap focuses on modernization, not state restoration
- We keep the 6-platform incremental wisdom but apply it to config flow

**What We Kept:**
- ✅ Incremental release philosophy
- ✅ Thorough testing between releases
- ✅ Risk assessment per release
- ✅ Clear success criteria
- ✅ Rollback planning

---

## Risk Mitigation

### Overall Strategy

1. **Incremental Releases:** One feature at a time, fully tested
2. **Clear Dependencies:** Architecture before features
3. **Backward Compatibility:** YAML config works throughout transition
4. **Rollback Safety:** Each release can be downgraded safely
5. **Testing Rigor:** 2-5 days testing per release
6. **User Communication:** Clear release notes and migration guides

### Specific Mitigations

**Device Registry (v1.4.0):**
- **Risk:** Entities don't link to device
- **Mitigation:** Test with fresh install and upgrade path
- **Rollback:** Device created but not required for entity function

**Platform Loading (v1.5.0):**
- **Risk:** Platforms fail to load
- **Mitigation:** Test all 7 platforms individually
- **Rollback:** Old method still in git history

**Config Flow (v1.6.0):**
- **Risk:** Breaks existing YAML setups
- **Mitigation:** Keep YAML loading parallel, test both paths
- **Rollback:** YAML config untouched, can downgrade

**YAML Import (v1.7.0):**
- **Risk:** Duplicate entries or failed migration
- **Mitigation:** Check for existing entries, log migration clearly
- **Rollback:** Can delete config entry, re-add YAML

### Release Checklist (Every Release)

- [ ] Code reviewed for Home Assistant best practices
- [ ] All tests pass (when we add them)
- [ ] Manual testing completed (3+ restart cycles)
- [ ] Fresh install tested
- [ ] Upgrade path tested
- [ ] Logs reviewed (no errors/warnings)
- [ ] CHANGELOG.md updated
- [ ] README.md updated if needed
- [ ] Release notes drafted
- [ ] Tag created and pushed
- [ ] GitHub release published
- [ ] Monitor for 48 hours before next release

---

## Success Metrics

### Per Release

**Quantitative:**
- Zero entity load failures
- Zero exceptions in logs
- Zero deprecation warnings
- Rollback rate < 2%

**Qualitative:**
- No user-reported issues
- Positive community feedback
- Documentation clear and complete

### Phase 1 Success (v1.4.0-v1.5.0)

- [ ] Device registry shows single Crestron device
- [ ] All entities linked to device
- [ ] No deprecated API warnings
- [ ] Zero regressions from v1.3.0
- [ ] Platform loading modernized

### Phase 2 Success (v1.6.0-v1.7.0)

- [ ] Config flow works for new installations
- [ ] YAML configs automatically migrated
- [ ] Both YAML and UI methods work
- [ ] No setup failures
- [ ] Clear migration path documented

### Phase 3 Success (v1.8.0-v1.11.0)

- [ ] Entity categories properly assigned
- [ ] Cover stop bug fixed
- [ ] Sync optimization working
- [ ] Type hints complete
- [ ] Code quality professional-grade

### Final Success (v1.11.0)

- [ ] Integration meets HA quality scale: Gold tier
- [ ] No known critical bugs
- [ ] Modern architecture throughout
- [ ] Fully tested and documented
- [ ] Ready for HACS default repositories (if desired)

---

## Timeline Estimate

### Conservative Timeline (Weekend Development)

| Release | Coding | Testing | Docs | Total | Cumulative |
|---------|--------|---------|------|-------|------------|
| v1.4.0 | 3h | 3 days | 1 day | 4 days | 4 days |
| v1.5.0 | 4h | 5 days | 1 day | 6 days | 10 days |
| v1.6.0 | 8h | 7 days | 2 days | 9 days | 19 days |
| v1.7.0 | 4h | 5 days | 1 day | 6 days | 25 days |
| v1.8.0 | 2h | 3 days | 1 day | 4 days | 29 days |
| v1.9.0 | 1h | 3 days | 0.5 day | 3.5 days | 32.5 days |
| v1.10.0 | 2h | 4 days | 1 day | 5 days | 37.5 days |
| v1.11.0 | 6h | 3 days | 1 day | 4 days | 41.5 days |

**Total: ~42 days (~6 weeks)**

**Real-World (Weekends Only): ~12-16 weeks calendar time**

### Aggressive Timeline (Dedicated Development)

If working full-time:
- Phase 1: 2 weeks
- Phase 2: 3 weeks
- Phase 3: 2 weeks
- **Total: 7 weeks**

---

## Next Steps

### ✅ COMPLETED (2025-11-11)

1. ✅ Review roadmap
2. ✅ Validate current state (v1.5.5)
3. ✅ Implement v1.4.0 (device registry)
4. ✅ Implement v1.5.0 (platform loading)
5. ✅ Fix v1.5.1-v1.5.5 (port attribute, cover stop)
6. ✅ Test extensively (all platforms working)
7. ✅ Update documentation
8. ✅ Phase 1 COMPLETE!

### 🎯 NEXT: v1.6.0 Implementation (This Week/Next Week)

**Status:** Ready to begin

1. ⬜ Review v1.6.0_CONFIG_FLOW_PLAN.md (updated)
2. ⬜ Create feature branch `feature/v1.6.0-config-flow`
3. ⬜ Implement Step 1-9 (config flow, async_setup_entry, platforms)
4. ⬜ Execute Test #1-9 (comprehensive testing)
5. ⬜ Update CHANGELOG.md and README.md
6. ⬜ Release v1.6.0
7. ⬜ Monitor for 48 hours

### Then: v1.7.0 - YAML Import (2-3 weeks later)

1. ⬜ Implement YAML import flow
2. ⬜ Test migration paths
3. ⬜ Release v1.7.0

### Then: v1.8.0, v1.10.0, v1.11.0 - Polish (4-6 weeks)

1. ⬜ v1.8.0: Entity categories
2. ⬜ v1.10.0: Sync optimization
3. ⬜ v1.11.0: Type hints
4. ⬜ Final testing and documentation
5. ⬜ Celebrate! 🎉

---

## Appendix: Technical Details

### Device Info Implementation Pattern

```python
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

class CrestronEntity:
    def __init__(self, hub, config):
        self._hub = hub
        # ... existing init ...

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"crestron_{self._hub.port}")},
            name="Crestron Control System",
            manufacturer="Crestron Electronics",
            model="XSIG Gateway",
            sw_version="1.4.0",  # Update per release
        )
```

### Config Entry Data Structure

```python
# Config entry data format
{
    "port": 16384,  # XSIG port
    # Entity config still in YAML for v1.x
    # Future: could move to entry.options
}
```

### Platform Loading Migration

```python
# OLD (deprecated)
for platform in PLATFORMS:
    hass.async_create_task(
        async_load_platform(hass, platform, DOMAIN, {}, config)
    )

# NEW (modern)
async def async_setup_entry(hass, entry):
    """Set up from config entry."""
    # ... setup hub ...
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
```

---

## Conclusion

This roadmap represents a **pragmatic, architecture-first approach** to modernizing the Crestron integration. By building on the solid foundation already in place (v1.3.0), we can incrementally add modern Home Assistant features without breaking existing functionality.

**Key Principles:**
1. Architecture before features
2. One change per release
3. Test thoroughly between releases
4. Maintain backward compatibility
5. Clear migration paths

**What Makes This Plan Different:**
- Recognizes v1.3.0 achievements (unique IDs, RestoreEntity already done)
- Focuses on what's actually missing (config flow, device registry)
- Correct architectural ordering to avoid rework
- Incremental releases proven safe by v1.3.0 success

**Confidence Level:** HIGH
- v1.3.0 shows the integration is stable
- RestoreEntity implementation proves we can do incremental releases
- Clear dependencies and ordering minimize risk
- Each release is independently testable

**Expected Outcome:** By v1.11.0, the Crestron integration will be a modern, well-architected Home Assistant integration that follows all current best practices while maintaining the stability and functionality users rely on.

---

**Document Version:** 2.0
**Last Updated:** 2025-11-11
**Next Review:** After v1.4.0 completion
**Owner:** @adamjs83
**Status:** APPROVED FOR IMPLEMENTATION
