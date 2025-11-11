# RestoreEntity Implementation Plan for Crestron XSIG Integration

## Executive Summary

This plan outlines a safe, incremental approach to adding `RestoreEntity` functionality to the Crestron XSIG integration, learning from the critical failures in v1.2.0-v1.2.2. The recommended approach prioritizes safety through complexity-based rollout with extensive validation.

**Recommended Strategy:** Option B (By Complexity) with 6 micro-releases
**Estimated Timeline:** 3-4 weeks (assuming 2-3 day testing cycles per release)
**Risk Level:** LOW (if followed exactly)

---

## 1. What RestoreEntity Does and Why We Need It

### Purpose of RestoreEntity

`RestoreEntity` is a Home Assistant mixin class that provides automatic state persistence across restarts. When an entity inherits from `RestoreEntity`, Home Assistant will:

1. **Save state on shutdown** - Automatically persist entity state and attributes to the state machine
2. **Restore on startup** - Provide access to the last known state via `async_get_last_state()`
3. **Handle unavailability gracefully** - Allow entities to show their last known state even when the underlying device is temporarily unavailable

### Why Crestron XSIG Needs It

**Current Problem:**
When Home Assistant restarts, all Crestron entities show as "unavailable" or have default values (lights off, climate at 0°C, etc.) until Crestron sends feedback. This can take:
- 5-30 seconds for initial connection
- Minutes if Crestron processor is slow to respond
- Indefinitely if specific joins never receive feedback

**Benefits:**
1. **Better UX** - Dashboard shows last known states immediately instead of "unavailable"
2. **Automation Continuity** - Automations can use last known states during startup window
3. **Visual Consistency** - UI doesn't flash from unavailable → actual state
4. **Diagnostics** - Can compare restored vs. actual state to detect issues

### What RestoreEntity Does NOT Do

- ❌ Does not automatically apply restored state back to the physical device
- ❌ Does not replace the need for actual Crestron feedback
- ❌ Does not guarantee the restored state matches current physical state
- ✅ Only provides a fallback until real data arrives

---

## 2. Post-Mortem: What Went Wrong in v1.2.0-v1.2.2

### Issue #1: Socket Exception - Premature Command Sending

**Root Cause:**
```python
async def async_added_to_hass(self):
    await super().async_added_to_hass()
    last_state = await self.async_get_last_state()
    if last_state:
        self._state = last_state.state  # Triggers property setter
        # Property setter calls self._hub.send_digital() IMMEDIATELY
```

**Timeline:**
1. Entity added to hass during setup
2. `async_added_to_hass()` called BEFORE connection established
3. Restored state applied
4. Property setter tries to send to Crestron
5. **BOOM** - Socket not connected yet

**Why It Happened:**
- Entity setup happens in parallel with connection establishment
- No guard to prevent sending during initial restore
- Confused "restoring state for display" with "setting state on device"

**Lesson:** Never trigger Crestron commands in `async_added_to_hass()` or `async_get_last_state()` flow

---

### Issue #2: Invalid HVAC Mode - String Contamination

**Root Cause:**
```python
if last_state and last_state.state:
    self._hvac_mode = last_state.state  # State is string "unavailable"
    # Later...

@property
def hvac_mode(self):
    return self._hvac_mode  # Returns "unavailable" string
    # Home Assistant expects HVACMode enum!
```

**Why It Happened:**
- State machine stores state as strings ("on", "off", "unavailable", "unknown")
- Climate entity returned raw string without validation
- `HVACMode` is an enum, not a string
- "unavailable" and "unknown" are sentinel values, not valid modes

**The Error:**
```
ValueError: 'unavailable' is not a valid HVACMode
```

**Lesson:** Always validate restored strings against enums and skip sentinel values

---

### Issue #3: Logging Flood - 200+ Debug Messages Per Startup

**Root Cause:**
```python
@property
def is_on(self):
    _LOGGER.debug("Getting is_on for %s", self.name)  # Called 10+ times per entity
    if self._hub.has_digital_value(self._join):
        _LOGGER.debug("Has value: %s", self._hub.get_digital(self._join))
        return self._hub.get_digital(self._join)
    if self._restored_state:
        _LOGGER.debug("Using restored state: %s", self._restored_state)
        return self._restored_state
    _LOGGER.debug("Returning default False")
    return False
```

**Why It Happened:**
- Debug logging in property getters
- Properties called multiple times during entity registration
- Properties called on every state update
- Multiplied by 20-30 entities = log explosion

**The Math:**
- 25 entities × 10 property calls per setup = 250 calls
- 4 debug lines per call = 1000 log lines
- Before any actual data received!

**Lesson:** Never put debug logging in property getters or hot paths

---

### Issue #4: Entities Not Loading on Second Reboot

**Root Cause (Suspected):**
```python
async def async_added_to_hass(self):
    await super().async_added_to_hass()  # RestoreEntity saves state here
    last_state = await self.async_get_last_state()
    # Some state restoration logic
    # BUT: If this raised an exception during first boot...
    # State was partially saved, leaving entity in invalid state
```

**Why It Happened (Theory):**
1. First boot: Exception during restore → entity setup incomplete
2. State machine saved partial/invalid state
3. Second boot: Tried to restore invalid state → setup failed silently
4. Entity never registered properly

**Alternative Theory:**
- Unique ID collision if restored state contained duplicate IDs
- Entity registry got corrupted by invalid state writes

**Lesson:** All exceptions during restore must be caught and logged, never allowed to bubble up

---

## 3. Safe Implementation Strategy: Recommended Approach

### ✅ RECOMMENDED: Option B - By Complexity (6 Micro-Releases)

**Rationale:**
1. **Risk Isolation** - Start with simplest platforms to validate pattern
2. **Pattern Refinement** - Learn from simple cases before tackling complex ones
3. **User Impact** - Simple platforms (switches) most commonly used, deliver value early
4. **Debugging** - Easy to isolate issues when only one platform type changes
5. **Rollback** - Can stop at any point without leaving integration half-done

### Release Sequence

#### **v1.3.1: Simple Boolean Platforms**
**Platforms:** `switch.py`, `binary_sensor.py`
- **Why First:**
  - Only boolean state (on/off, detected/clear)
  - No attributes to restore
  - No enums to validate
  - Can't send commands (binary_sensor is read-only)
- **Risk:** VERY LOW
- **Testing Time:** 2-3 days
- **Lines Changed:** ~40

---

#### **v1.3.2: Light Platform**
**Platform:** `light.py`
- **Why Second:**
  - Boolean state + one numeric attribute (brightness)
  - Well-defined validation (0-255)
  - Common platform, good user feedback
  - Tests numeric restoration pattern
- **Risk:** LOW
- **Testing Time:** 2-3 days
- **Lines Changed:** ~50

---

#### **v1.3.3: Sensor Platform**
**Platform:** `sensor.py`
- **Why Third:**
  - Numeric or string values
  - No commands sent (read-only)
  - Tests unit validation
  - Tests None vs 0 vs "unknown"
- **Risk:** LOW
- **Testing Time:** 2-3 days
- **Lines Changed:** ~35

---

#### **v1.3.4: Cover Platform**
**Platform:** `cover.py`
- **Why Fourth:**
  - Position attribute (0-100)
  - Enum state (open/closed/opening/closing)
  - Tests enum validation pattern before climate
  - Less complex than climate
- **Risk:** MEDIUM
- **Testing Time:** 3-4 days
- **Lines Changed:** ~60

---

#### **v1.3.5: Climate Platform**
**Platform:** `climate.py`
- **Why Fifth:**
  - Most complex state model
  - Multiple enums (hvac_mode, fan_mode, preset)
  - Multiple numeric attributes (temp, humidity)
  - Caused the v1.2.0 failures
  - Need patterns proven from cover first
- **Risk:** MEDIUM-HIGH
- **Testing Time:** 4-5 days
- **Lines Changed:** ~80

---

#### **v1.3.6: Media Player Platform**
**Platform:** `media_player.py`
- **Why Last:**
  - Complex state enum (playing/paused/idle/off)
  - Multiple attributes (volume, source, media title)
  - Least commonly used in Crestron setups
  - Can apply all learned patterns
- **Risk:** MEDIUM
- **Testing Time:** 3-4 days
- **Lines Changed:** ~70

---

## 4. Standard Property Implementation Pattern

### The Safe Pattern for All Properties

```python
@property
def some_property(self):
    """Return some value.

    Priority:
    1. Real data from Crestron (most current)
    2. Restored value from last known state (fallback)
    3. None or safe default (unknown)
    """
    # Priority 1: Check if we have REAL data from Crestron
    if self._hub.has_digital_value(self._join):
        return self._hub.get_digital(self._join)

    # Priority 2: Use restored value if available
    if self._restored_value is not None:
        return self._restored_value

    # Priority 3: Return safe default
    return None  # Or False, or 0, depending on property type
```

**Key Points:**
- ✅ Always check real data FIRST
- ✅ Restored value is FALLBACK only
- ✅ Never assume restored value exists (check `is not None`)
- ✅ Always have a safe default

---

### Boolean Property Pattern

```python
@property
def is_on(self) -> bool | None:
    """Return True if entity is on.

    Returns:
        True if on, False if off, None if unknown
    """
    # Real data from Crestron
    if self._hub.has_digital_value(self._on_join):
        return self._hub.get_digital(self._on_join)

    # Restored boolean (could be True, False, or None)
    if self._restored_is_on is not None:
        return self._restored_is_on

    # Unknown state - return None, not False!
    return None
```

---

### Enum Property Pattern (CRITICAL for Climate)

```python
@property
def hvac_mode(self) -> HVACMode:
    """Return current HVAC mode.

    Returns:
        HVACMode enum value, never a string
    """
    # Real data from Crestron
    if self._hvac_mode_join and self._hub.has_analog_value(self._hvac_mode_join):
        crestron_value = self._hub.get_analog(self._hvac_mode_join)
        return self._crestron_to_hvac_mode(crestron_value)

    # Restored mode (already validated as HVACMode enum in async_added_to_hass)
    if self._restored_hvac_mode is not None:
        return self._restored_hvac_mode

    # Safe default - MUST be a valid enum value
    return HVACMode.OFF  # Never return None or string!
```

**Critical Points:**
- ✅ NEVER return a string - always return enum
- ✅ NEVER return None - always return valid enum value
- ✅ Restored value is already validated enum
- ❌ NEVER do: `return last_state.state` (this is a string!)
- ✅ ALWAYS do: `return HVACMode.HEAT` (this is enum)

---

## 5. Validation Requirements by Platform

### Switch & Binary Sensor Validation

```python
async def async_added_to_hass(self):
    await super().async_added_to_hass()
    last_state = await self.async_get_last_state()

    if last_state and last_state.state not in ("unavailable", "unknown"):
        if last_state.state == "on":
            self._restored_is_on = True
        elif last_state.state == "off":
            self._restored_is_on = False
        else:
            _LOGGER.warning(
                "Invalid restored state '%s' for %s, ignoring",
                last_state.state, self.entity_id
            )
            self._restored_is_on = None
    else:
        self._restored_is_on = None
```

**Invalid States to Skip:**
- "unavailable"
- "unknown"
- None
- Any string that isn't "on" or "off"

---

### Light Validation

```python
async def async_added_to_hass(self):
    await super().async_added_to_hass()
    last_state = await self.async_get_last_state()

    if last_state and last_state.state not in ("unavailable", "unknown"):
        if last_state.state == "on":
            self._restored_is_on = True
            # Restore brightness if present
            if last_state.attributes:
                brightness = last_state.attributes.get("brightness")
                if brightness is not None:
                    try:
                        brightness = int(brightness)
                        if 0 <= brightness <= 255:
                            self._restored_brightness = brightness
                        else:
                            _LOGGER.warning(
                                "Invalid brightness %s for %s, ignoring",
                                brightness, self.entity_id
                            )
                    except (ValueError, TypeError):
                        _LOGGER.warning("Cannot convert brightness to int")
        elif last_state.state == "off":
            self._restored_is_on = False
            self._restored_brightness = None
```

**Invalid States to Skip:**
- State: "unavailable", "unknown", None
- Brightness: < 0, > 255, non-numeric

---

### Climate Validation (MOST CRITICAL)

```python
from homeassistant.components.climate import HVACMode, FanMode

async def async_added_to_hass(self):
    await super().async_added_to_hass()
    last_state = await self.async_get_last_state()

    if not last_state or last_state.state in ("unavailable", "unknown"):
        self._restored_hvac_mode = None
        self._restored_target_temp = None
        return

    # Restore HVAC mode - CRITICAL VALIDATION
    try:
        # Validate against HVACMode enum
        self._restored_hvac_mode = HVACMode(last_state.state)
    except (ValueError, AttributeError) as err:
        _LOGGER.warning(
            "Cannot restore HVAC mode '%s' for %s: %s",
            last_state.state, self.entity_id, err
        )
        self._restored_hvac_mode = None

    # Restore attributes if state was valid
    if last_state.attributes:
        # Target temperature
        target_temp = last_state.attributes.get("temperature")
        if target_temp is not None:
            try:
                target_temp = float(target_temp)
                # Validate against min/max if defined
                if hasattr(self, '_min_temp') and hasattr(self, '_max_temp'):
                    if self._min_temp <= target_temp <= self._max_temp:
                        self._restored_target_temp = target_temp
                else:
                    self._restored_target_temp = target_temp
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid target temperature")
```

**Invalid States to Skip:**
- HVAC mode: "unavailable", "unknown", None, any string not in HVACMode enum
- Temperatures: None, non-numeric, outside min/max range
- Fan mode: Any string not in FanMode enum

---

## 6. Testing Strategy

### Testing Requirements (Every Release)

**For EVERY release:**

1. ✅ **Clean Install Test** - Fresh Home Assistant with integration
2. ✅ **Upgrade Test** - Upgrade from v1.3.0 to new version
3. ✅ **Multi-Restart Test** - At least 3 restart cycles
4. ✅ **Connection Loss Test** - Unplug Crestron, restart HA, reconnect
5. ✅ **Log Review** - Check for warnings/errors in full log

### Test Cycle Template

1. **Initial State Setup**
   - Set entities to known states
   - Wait for Crestron feedback confirmation
   - Verify states in HA dashboard

2. **First Restart**
   - Restart Home Assistant
   - IMMEDIATELY check dashboard (within 5 seconds)
   - Expected: Entities show last states (not "unavailable")
   - Wait for Crestron connection
   - Expected: States remain correct or update if changed

3. **Second Restart (Critical - Where v1.2 Failed)**
   - Change some entities physically on Crestron
   - Restart Home Assistant
   - Expected: All entities load successfully
   - Expected: States show restored or new values

4. **Connection Loss Test**
   - Unplug Crestron processor
   - Restart Home Assistant
   - Expected: Entities show restored states
   - Expected: Entities marked as unavailable after timeout
   - Reconnect Crestron
   - Expected: States update from Crestron

### Log Checks

```bash
# Search for errors
grep -i "error" home-assistant.log | grep crestron
grep -i "exception" home-assistant.log | grep crestron

# Check for v1.2.0 errors
grep "is not a valid.*Mode" home-assistant.log

# Count debug messages - should be minimal
grep "DEBUG.*crestron" home-assistant.log | wc -l
# Expected: < 50 lines
# Bad: > 200 lines
```

### Success Criteria (Every Release)

- [ ] All entities load on first restart
- [ ] All entities load on second restart
- [ ] All entities load on third restart
- [ ] Restored states match last known states
- [ ] No exceptions in log
- [ ] No "unavailable is not valid" errors
- [ ] < 50 debug log lines total
- [ ] States update correctly when Crestron sends feedback

---

## 7. Critical Pitfalls to AVOID

### ❌ PITFALL #1: Restoring Sentinel Values

**Wrong:**
```python
self._restored_state = last_state.state  # Could be "unavailable"!
```

**Right:**
```python
if last_state and last_state.state not in ("unavailable", "unknown"):
    self._restored_state = self._validate_state(last_state.state)
```

---

### ❌ PITFALL #2: Sending Commands During Restore

**Wrong:**
```python
async def async_added_to_hass(self):
    last_state = await self.async_get_last_state()
    if last_state and last_state.state == "on":
        await self.async_turn_on()  # ❌ Sends to Crestron!
```

**Right:**
```python
async def async_added_to_hass(self):
    last_state = await self.async_get_last_state()
    if last_state and last_state.state == "on":
        self._restored_is_on = True  # ✅ Just store for display
```

---

### ❌ PITFALL #3: No Enum Validation

**Wrong:**
```python
self._hvac_mode = last_state.state  # ❌ String, not enum!
```

**Right:**
```python
if last_state and last_state.state not in ("unavailable", "unknown"):
    try:
        self._restored_hvac_mode = HVACMode(last_state.state)
    except ValueError:
        _LOGGER.warning("Invalid HVAC mode: %s", last_state.state)
        self._restored_hvac_mode = None
```

---

### ❌ PITFALL #4: Debug Logging in Properties

**Wrong:**
```python
@property
def is_on(self):
    _LOGGER.debug("Getting is_on")  # ❌ Called 100+ times!
    ...
```

**Right:**
```python
@property
def is_on(self):
    # ✅ NO logging in properties!
    if self._hub.has_digital_value(self._join):
        return self._hub.get_digital(self._join)
    return self._restored_is_on
```

---

### ❌ PITFALL #5: Wrong Priority Order

**Wrong:**
```python
@property
def is_on(self):
    # ❌ Restored first - WRONG!
    if self._restored_is_on is not None:
        return self._restored_is_on
    if self._hub.has_digital_value(self._join):
        return self._hub.get_digital(self._join)
```

**Right:**
```python
@property
def is_on(self):
    # ✅ Real data ALWAYS takes priority
    if self._hub.has_digital_value(self._join):
        return self._hub.get_digital(self._join)
    if self._restored_is_on is not None:
        return self._restored_is_on
    return None
```

---

### ❌ PITFALL #6: Not Handling None Values

**Wrong:**
```python
if self._restored_is_on:  # ❌ Skips False values!
    return self._restored_is_on
```

**Right:**
```python
if self._restored_is_on is not None:  # ✅ Allows False through
    return self._restored_is_on
```

---

### ❌ PITFALL #7: Unhandled Exceptions

**Wrong:**
```python
async def async_added_to_hass(self):
    # ❌ If this raises, entity setup fails!
    self._restored_brightness = int(last_state.attributes["brightness"])
```

**Right:**
```python
async def async_added_to_hass(self):
    try:
        last_state = await self.async_get_last_state()
        if last_state and last_state.attributes:
            brightness = last_state.attributes.get("brightness")
            if brightness is not None:
                try:
                    self._restored_brightness = int(brightness)
                except (ValueError, TypeError) as err:
                    _LOGGER.warning("Cannot restore brightness: %s", err)
    except Exception as err:
        _LOGGER.error("Error restoring state: %s", err, exc_info=True)
        # ✅ Entity still loads, just without restored state
```

---

## 8. Rollback Plan

### When to Rollback

**Immediate Rollback Needed:**
```bash
# These errors indicate critical failure
grep -i "is not a valid.*Mode" home-assistant.log
grep -i "socket.*not connected" home-assistant.log
grep -i "error.*async_added_to_hass" home-assistant.log
```

**User Reports:**
- "Entities not loading after update"
- "Climate showing errors in log"
- "Home Assistant won't start"

### Rollback Procedure

```bash
# User instructions
1. Stop Home Assistant
2. Open HACS
3. Find "Crestron XSIG"
4. Click "Redownload"
5. Select version "v1.3.0"
6. Restart Home Assistant
```

**No Data Loss:**
- RestoreEntity only affects display
- No Crestron configuration changes
- Rolling back just removes the restore feature

---

## 9. Timeline Estimate

### Conservative Timeline

| Release | Coding | Testing | Documentation | Total | Cumulative |
|---------|--------|---------|---------------|-------|------------|
| v1.3.1 | 2h | 2 days | 0.5 day | 3 days | 3 days |
| v1.3.2 | 2h | 2 days | 0.5 day | 3 days | 6 days |
| v1.3.3 | 2h | 2 days | 0.5 day | 3 days | 9 days |
| v1.3.4 | 3h | 3 days | 0.5 day | 4 days | 13 days |
| v1.3.5 | 4h | 5 days | 1 day | 7 days | 20 days |
| v1.3.6 | 3h | 3 days | 0.5 day | 4 days | 24 days |

**Total: 24 days (~3.5 weeks)**

**Real-World (Weekends Only): ~8 weekends = 2 months calendar time**

---

## 10. Success Metrics

**Per Release:**
- [ ] Zero entity load failures
- [ ] Zero exceptions in logs
- [ ] < 5 user-reported issues
- [ ] Rollback rate < 2%

**Final Success (All Platforms Complete):**
- [ ] All 6 platform types support RestoreEntity
- [ ] Zero known critical bugs
- [ ] < 10 total user issues
- [ ] Positive user feedback
- [ ] No regression in functionality

---

## 11. Next Steps

1. **Review this plan**
2. **Set up test environment**
3. **Create feature branch** for v1.3.1
4. **Implement v1.3.1** following patterns above
5. **Test extensively** (3+ restart cycles)
6. **Document** (CHANGELOG, README)
7. **Release v1.3.1**
8. **Monitor for 3-5 days**
9. **Proceed to v1.3.2** if stable

---

## 12. Key Success Factors

1. **DO NOT RUSH** - v1.2.0 failed because of rushing
2. **TEST EXTENSIVELY** - Especially climate platform
3. **VALIDATE EVERYTHING** - Enums, ranges, types
4. **LOG WISELY** - Warnings for failures, no debug spam
5. **NEVER SEND COMMANDS** - During restore or from properties
6. **PRIORITIZE REAL DATA** - Restored is fallback only
7. **HANDLE EXCEPTIONS** - Don't let restore failures break entity load
8. **COMMUNICATE CLEARLY** - Users need to know what to expect

---

## Conclusion

RestoreEntity is a valuable feature that significantly improves user experience. The v1.2.0 failures demonstrated that **rushing leads to critical bugs**.

**The incremental approach:**
- ✅ Minimizes risk through isolation
- ✅ Delivers value progressively
- ✅ Allows learning and pattern refinement
- ✅ Provides safe rollback at every step
- ✅ Builds user confidence through stability

**Time investment:** 8 weeks
**Value delivered:** Professional-grade state restoration
**Risk:** LOW (with discipline and testing)

**Recommendation:** PROCEED with incremental releases, strict testing, and zero tolerance for shortcuts.

---

*Plan created: 2025-11-11*
*Target completion: 2025-01-XX (8 weeks from start)*
*Target stability: v1.4.0 (all platforms complete)*
