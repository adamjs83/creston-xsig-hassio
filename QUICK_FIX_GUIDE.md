# v1.5.1 HOTFIX - Quick Fix Guide

**2-Minute Implementation Guide**

---

## The Error

```
AttributeError: 'CrestronXsig' object has no attribute 'port'
```

---

## The Fix (2 Lines)

**File:** `/Users/adamjs83/Library/Mobile Documents/com~apple~CloudDocs/aiworkflows/crestron/custom_components/crestron/crestron.py`

### Line 1: Add to __init__ method (around line 22)

```python
class CrestronXsig:
    def __init__(self):
        """ Initialize CrestronXsig object """
        self._digital = {}
        self._analog = {}
        self._serial = {}
        self._digital_received = set()
        self._analog_received = set()
        self._serial_received = set()
        self._writer = None
        self._callbacks = set()
        self._server = None
        self._available = False
        self._sync_all_joins_callback = None
        self.port = None  # ← ADD THIS LINE
```

### Line 2: Add to listen method (around line 25)

```python
async def listen(self, port):
    """ Start TCP XSIG server listening on configured port """
    self.port = port  # ← ADD THIS LINE
    server = await asyncio.start_server(self.handle_connection, "0.0.0.0", port)
    # ... rest of method
```

---

## Verify

```bash
cd "/Users/adamjs83/Library/Mobile Documents/com~apple~CloudDocs/aiworkflows/crestron/custom_components/crestron"
python3 -m py_compile crestron.py
```

Should complete with no errors.

---

## Test

1. Restart Home Assistant
2. Check logs - should see: `Listening on 0.0.0.0:16384`
3. Verify no `AttributeError`
4. Verify all entities load

---

## Done!

**That's it.** 2 lines added to 1 file fixes all 7 affected platforms.

**Full details:** See `v1.5.1_HOTFIX_PLAN.md`
**Architecture:** See `ARCHITECTURE_DIAGRAM.md`
**Summary:** See `HOTFIX_IMPLEMENTATION_SUMMARY.md`
