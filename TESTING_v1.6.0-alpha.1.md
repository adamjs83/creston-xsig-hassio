# v1.6.0-alpha.1 Testing Guide

**Status:** ✅ READY FOR TESTING  
**Version:** v1.6.0-alpha.1  
**Tag:** `v1.6.0-alpha.1`  
**Branch:** `feature/v1.6.0-config-flow`  
**Date:** 2025-11-16

---

## ⚠️ ALPHA WARNING

**This is an ALPHA release for testing purposes only.**

- ❌ DO NOT use in production
- ✅ Test in a development/test Home Assistant instance
- 🐛 Report any issues on GitHub
- 📝 Provide detailed feedback

---

## Installation via HACS

### Method 1: Install from Tag (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Search for "Crestron XSIG Integration"
4. Click "Download"
5. **Select version:** `v1.6.0-alpha.1`
6. Click "Download"
7. **Restart Home Assistant**

### Method 2: Install from Branch

1. HACS → Integrations → ⋮ → Custom repositories
2. Add repository URL
3. Category: Integration
4. Search for "Crestron"
5. Install
6. Select branch: `feature/v1.6.0-config-flow`
7. **Restart Home Assistant**

---

## Test Scenarios (9 Tests)

### ✅ Test #1: Fresh Install via UI Only

**Goal:** Verify config flow works for new users

**Prerequisites:**
- No existing Crestron configuration
- Clean Home Assistant instance

**Steps:**
1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Crestron"
4. Enter port: 16384 (or your XSIG port)
5. Click "Submit"

**Expected Results:**
- ✅ Config flow completes successfully
- ✅ "Crestron Control System" device appears in Devices
- ✅ Device shows manufacturer, model, sw_version
- ✅ No errors in logs

**Validation:**
```yaml
# No YAML config needed for this test
```

---

### ✅ Test #2: Fresh Install via YAML Only

**Goal:** Verify YAML path still works (backward compatibility)

**Prerequisites:**
- No existing Crestron configuration
- Clean Home Assistant instance

**Steps:**
1. Add YAML configuration:
```yaml
crestron:
  port: 16384
  
light:
  - platform: crestron
    name: Test Light
    brightness_join: 1
```
2. Restart Home Assistant
3. Check Settings → Devices & Services

**Expected Results:**
- ✅ Integration loads from YAML
- ✅ Test Light entity appears
- ✅ Device appears in device registry
- ✅ No errors in logs

---

### ✅ Test #3: Upgrade from v1.5.5 with YAML (CRITICAL!)

**Goal:** Most important test - verify existing users aren't broken

**Prerequisites:**
- Running v1.5.5 with working YAML config
- Existing entities working

**Steps:**
1. Document current state:
   - List all entity IDs
   - Screenshot device page
   - Check entity unique IDs
2. Upgrade to v1.6.0-alpha.1 via HACS
3. Restart Home Assistant
4. Verify everything still works

**Expected Results:**
- ✅ All existing entities still work
- ✅ No entity ID changes
- ✅ No unique ID changes
- ✅ Device appears in registry now (if not before)
- ✅ No errors in logs
- ✅ All functionality preserved

**CRITICAL:** If this test fails, DO NOT proceed. Report immediately.

---

### ✅ Test #4: YAML + UI Conflict Handling

**Goal:** Verify dual configuration detection works

**Prerequisites:**
- Existing YAML config on port 16384

**Steps:**
1. Have YAML config active:
```yaml
crestron:
  port: 16384
```
2. Go to Settings → Devices & Services
3. Click "+ Add Integration"
4. Search for "Crestron"
5. Enter port: 16384 (same port!)
6. Click "Submit"

**Expected Results:**
- ✅ Config entry created successfully
- ✅ Persistent notification appears warning about dual config
- ✅ YAML hub continues to work (takes precedence)
- ✅ No duplicate hubs created
- ✅ Log warning about dual configuration

---

### ✅ Test #5: Device Registry Verification

**Goal:** Verify device appears correctly in UI

**Prerequisites:**
- Config entry OR YAML config active

**Steps:**
1. Go to Settings → Devices & Services → Devices
2. Find "Crestron Control System"
3. Click on device
4. Check device page

**Expected Results:**
- ✅ Device name: "Crestron Control System"
- ✅ Manufacturer: "Crestron Electronics"
- ✅ Model: "XSIG Gateway"
- ✅ Software version: "1.6.0"
- ✅ All entities linked to device
- ✅ Entities appear in device page entity list

---

### ✅ Test #6: All 7 Platforms Still Work

**Goal:** Verify no regressions in platform functionality

**Prerequisites:**
- YAML config with entities from all platforms

**Test YAML:**
```yaml
crestron:
  port: 16384

light:
  - platform: crestron
    name: Test Light
    brightness_join: 1

switch:
  - platform: crestron
    name: Test Switch
    switch_join: 1

sensor:
  - platform: crestron
    name: Test Sensor
    value_join: 1

binary_sensor:
  - platform: crestron
    name: Test Binary Sensor
    is_on_join: 1

climate:
  - platform: crestron
    name: Test Thermostat
    type: standard
    heat_sp_join: 1
    cool_sp_join: 2
    reg_temp_join: 3
    # ... other joins

cover:
  - platform: crestron
    name: Test Shade
    pos_join: 1

media_player:
  - platform: crestron
    name: Test Media
    mute_join: 1
    volume_join: 2
```

**Expected Results:**
- ✅ All 7 platforms load successfully
- ✅ All entities appear and work
- ✅ All entities show correct device_info
- ✅ No platform errors in logs

---

### ✅ Test #7: Entry Reload and Removal

**Goal:** Verify config entry lifecycle management

**Prerequisites:**
- Config entry created (UI setup)

**Steps:**
1. Go to Settings → Devices & Services
2. Find Crestron integration
3. Click "⋮" → "Reload"
4. Wait for reload to complete
5. Click "⋮" → "Delete"
6. Confirm deletion

**Expected Results (Reload):**
- ✅ Entry reloads successfully
- ✅ Hub reconnects
- ✅ Device remains in registry
- ✅ No errors in logs

**Expected Results (Delete):**
- ✅ Entry removes successfully
- ✅ Hub stops properly
- ✅ Device removed from registry
- ✅ Config entry removed
- ✅ No errors in logs

---

### ✅ Test #8: Port Validation

**Goal:** Verify port validation works correctly

**Test Cases:**

**8a. Invalid Port (too low):**
- Enter port: 1023
- Expected: Error "Port must be between 1024 and 65535"

**8b. Invalid Port (too high):**
- Enter port: 65536
- Expected: Error "Port must be between 1024 and 65535"

**8c. Port in Use:**
- Start something on port 16384 first
- Try to add Crestron on port 16384
- Expected: Error "Port is already in use"

**8d. Duplicate Entry:**
- Create config entry on port 16384
- Try to create another on port 16384
- Expected: Abort "This port is already configured"

---

### ✅ Test #9: Multiple Instances (Advanced)

**Goal:** Verify multiple Crestron systems can coexist

**Prerequisites:**
- Access to 2 Crestron systems (or ability to test 2 ports)

**Steps:**
1. Add first Crestron: port 16384
2. Add second Crestron: port 16385
3. Verify both work

**Expected Results:**
- ✅ Two config entries created
- ✅ Two devices in registry
- ✅ Devices have different identifiers
- ✅ Both hubs connect successfully
- ✅ No port conflicts
- ✅ Entities can be linked to appropriate device

---

## Logging for Testing

Enable debug logging to catch issues:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.crestron: debug
```

Then check logs at Settings → System → Logs

---

## Common Issues & Solutions

### Issue: Config flow doesn't appear
**Solution:** Check HACS installed correctly, restart HA

### Issue: "Port in use" error
**Solution:** Check if v1.5.5 hub still running, restart HA

### Issue: Entities don't appear
**Solution:** Entities still come from YAML in v1.6.0, check YAML config

### Issue: Device doesn't appear
**Solution:** Check logs, verify device_info in entities

### Issue: Duplicate hubs
**Solution:** Remove one config (either YAML or UI), restart HA

---

## Reporting Issues

If you find bugs, please report on GitHub with:

1. **Description:** What went wrong?
2. **Steps to reproduce:** How can we recreate it?
3. **Expected behavior:** What should happen?
4. **Actual behavior:** What actually happened?
5. **Logs:** Relevant error messages
6. **Configuration:** Your YAML config (sanitized)
7. **Environment:**
   - Home Assistant version
   - Installation method (HACS)
   - v1.6.0-alpha.1

**GitHub Issues:** https://github.com/adamjs83/crestron_custom_component/issues

---

## Success Criteria

Before approving for stable release, ALL tests must pass:

- [ ] Test #1: Fresh UI install works
- [ ] Test #2: Fresh YAML install works
- [ ] Test #3: Upgrade from v1.5.5 works (CRITICAL!)
- [ ] Test #4: YAML/UI conflict handled correctly
- [ ] Test #5: Device appears in registry
- [ ] Test #6: All 7 platforms work
- [ ] Test #7: Reload and removal work
- [ ] Test #8: Port validation works
- [ ] Test #9: Multiple instances work

**If all tests pass → Release v1.6.0 stable**  
**If any test fails → Fix issues, release alpha.2**

---

## Next Steps After Testing

1. **If successful:**
   - Merge feature branch to main
   - Release v1.6.0 stable
   - Update CHANGELOG.md
   - Update README.md
   - Monitor for 48 hours

2. **If issues found:**
   - Document all issues
   - Fix in feature branch
   - Release v1.6.0-alpha.2
   - Re-test

3. **After v1.6.0 stable:**
   - Begin v1.7.0 (YAML import)
   - Monitor community feedback
   - Plan v1.8.0+ features

---

**Good luck with testing! 🚀**

_Document Version: 1.0_  
_Created: 2025-11-16_  
_For: v1.6.0-alpha.1 testing_
