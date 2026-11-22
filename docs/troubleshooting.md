# Troubleshooting

Covers: Debug logging and common issues.
Last verified: 2026-11-22 (split from README.md; content not re-verified)

## Troubleshooting

### Enable Debug Logging

```yaml
logger:
  default: info
  logs:
    custom_components.crestron: debug
```

### Common Issues

**Connection fails**
- Verify port number matches XSIG symbol
- Check network connectivity between HA and Crestron
- Verify firewall allows traffic on configured port

**State not updating**
- Check join numbers match between HA and Crestron
- Verify join types (digital/analog/serial) are correct
- Enable debug logging to see join updates

**Temperature values incorrect**
- Remember: temperature uses tenths (72.5°F = 725)
- Check divisor parameter in sensor configuration

**Button events not firing**
- Verify event type is `crestron_button_event`
- Check Developer Tools → Events to monitor events
- Confirm button press joins are triggering in debug logs

**LED not syncing**
- Verify LED binding is configured
- Check that bound entity exists and has valid state
- Confirm LED join matches button press join
