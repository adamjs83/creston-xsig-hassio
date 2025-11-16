"""The Crestron Integration Component"""

import asyncio
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, Context
from homeassistant.helpers import discovery, device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import TrackTemplate, async_track_template_result
from homeassistant.helpers.template import Template
from homeassistant.helpers.script import Script
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    CONF_VALUE_TEMPLATE,
    CONF_ATTRIBUTE,
    CONF_ENTITY_ID,
    STATE_ON,
    STATE_OFF,
    CONF_SERVICE,
    CONF_SERVICE_DATA,
)

from .crestron import CrestronXsig
from .const import CONF_PORT, HUB, DOMAIN, CONF_JOIN, CONF_SCRIPT, CONF_TO_HUB, CONF_FROM_HUB
#from .control_surface_sync import ControlSurfaceSync

_LOGGER = logging.getLogger(__name__)

TO_JOINS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_JOIN): cv.string,
        vol.Optional(CONF_ENTITY_ID): cv.entity_id,           
        vol.Optional(CONF_ATTRIBUTE): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template
    }
)

FROM_JOINS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_JOIN): cv.string,
        vol.Required(CONF_SCRIPT): cv.SCRIPT_SCHEMA
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_PORT): cv.port,
                vol.Optional(CONF_TO_HUB): vol.All(cv.ensure_list, [TO_JOINS_SCHEMA]),
                vol.Optional(CONF_FROM_HUB): vol.All(cv.ensure_list, [FROM_JOINS_SCHEMA])
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [
    "binary_sensor",
    "sensor",
    "switch",
    "light",
    "climate",
    "cover",
    "media_player",
]


async def async_setup(hass, config):
    """Set up a the crestron component."""

    if config.get(DOMAIN) is not None:
        hass.data[DOMAIN] = {}
        hub = CrestronHub(hass, config[DOMAIN])

        await hub.start()
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, hub.stop)

        # Load all platforms in parallel and wait for completion
        await asyncio.gather(
            *[
                discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
                for platform in PLATFORMS
            ]
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Crestron XSIG from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry containing port configuration

    Returns:
        True if setup successful, False otherwise
    """
    # Initialize domain data if not exists
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Check if YAML configuration exists on same port
    if HUB in hass.data[DOMAIN]:
        yaml_hub = hass.data[DOMAIN][HUB]
        # Check if it's the same port
        if hasattr(yaml_hub, 'port') and yaml_hub.port == entry.data[CONF_PORT]:
            _LOGGER.warning(
                "Crestron hub already configured via YAML on port %s. "
                "YAML configuration takes precedence. "
                "Remove YAML config to use UI configuration.",
                entry.data[CONF_PORT]
            )
            # Create a persistent notification to inform user
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "message": "Crestron XSIG is configured via both YAML and UI on port {}. "
                               "YAML configuration is being used. To use UI configuration, "
                               "remove the 'crestron:' section from configuration.yaml and restart.".format(
                                   entry.data[CONF_PORT]
                               ),
                    "title": "Crestron Dual Configuration",
                    "notification_id": f"crestron_dual_config_{entry.data[CONF_PORT]}"
                }
            )
            # Still return True so entry isn't marked failed
            # But we won't create a second hub
            return True

    # Create minimal hub config (port only for v1.6.0)
    hub_config = {CONF_PORT: entry.data[CONF_PORT]}

    # Create and start hub
    # set_hub_key=False prevents overwriting YAML's hub if it exists
    hub_wrapper = CrestronHub(hass, hub_config, set_hub_key=False)
    await hub_wrapper.start()

    # Store hub under entry ID (not at HUB key - that's for YAML)
    hass.data[DOMAIN][entry.entry_id] = {
        HUB: hub_wrapper.hub,  # Store CrestronXsig instance
        'port': entry.data[CONF_PORT],
        'entry': entry,
        'hub_wrapper': hub_wrapper,  # Store wrapper for cleanup
    }

    # Register stop handler
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, hub_wrapper.stop)
    )

    # Create device in registry
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"crestron_{entry.data[CONF_PORT]}")},
        name="Crestron Control System",
        manufacturer="Crestron Electronics",
        model="XSIG Gateway",
        sw_version="1.6.0",
    )

    # Forward entry setup to platforms
    # Note: For v1.6.0, platforms will just create device linkage
    # Actual entities still come from YAML configuration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(
        "Crestron XSIG config entry setup complete on port %s",
        entry.data[CONF_PORT]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to unload

    Returns:
        True if unload successful, False otherwise
    """
    _LOGGER.debug("Unloading Crestron config entry for port %s", entry.data[CONF_PORT])

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Get hub data
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)

        if entry_data:
            # Stop the hub
            hub_wrapper = entry_data.get('hub_wrapper')
            if hub_wrapper:
                # Create a dummy event for stop method
                class StopEvent:
                    pass
                hub_wrapper.stop(StopEvent())
                _LOGGER.info(
                    "Stopped Crestron hub on port %s",
                    entry_data.get('port')
                )

        # Dismiss dual config notification if exists
        await hass.services.async_call(
            "persistent_notification",
            "dismiss",
            {"notification_id": f"crestron_dual_config_{entry.data[CONF_PORT]}"}
        )

    return unload_ok


class CrestronHub:
    ''' Wrapper for the CrestronXsig library '''
    def __init__(self, hass, config, set_hub_key=True):
        self.hass = hass
        self.hub = CrestronXsig()
        self.port = config.get(CONF_PORT)
        self.context = Context()
        self.to_hub = {}
        self.tracker = None  # Initialize tracker to None
        self.from_hub = None  # Initialize from_hub to None

        # Only set the HUB key if requested (YAML sets it, config entry doesn't)
        # This prevents config entry from overwriting YAML's hub
        if set_hub_key:
            hass.data[DOMAIN][HUB] = self.hub

        self.hub.register_sync_all_joins_callback(self.sync_joins_to_hub)
        if CONF_TO_HUB in config:
            track_templates = []
            for entity in config[CONF_TO_HUB]:
                template_string = None
                if CONF_VALUE_TEMPLATE in entity:
                    template = entity[CONF_VALUE_TEMPLATE]
                    self.to_hub[entity[CONF_JOIN]] = template
                    track_templates.append(TrackTemplate(template, None))
                elif CONF_ATTRIBUTE in entity and CONF_ENTITY_ID in entity:
                    template_string = (
                        "{{state_attr('"
                        + entity[CONF_ENTITY_ID]
                        + "','"
                        + entity[CONF_ATTRIBUTE]
                        + "')}}"
                    )
                    template = Template(template_string, hass)
                    self.to_hub[entity[CONF_JOIN]] = template
                    track_templates.append(TrackTemplate(template, None))
                elif CONF_ENTITY_ID in entity:
                    template_string = "{{states('" + entity[CONF_ENTITY_ID] + "')}}"
                    template = Template(template_string, hass)
                    self.to_hub[entity[CONF_JOIN]] = template
                    track_templates.append(TrackTemplate(template, None))
            self.tracker = async_track_template_result(
                self.hass, track_templates, self.template_change_callback
            )
        if CONF_FROM_HUB in config:
            self.from_hub = config[CONF_FROM_HUB]
            self.hub.register_callback(self.join_change_callback)

    async def start(self):
        await self.hub.listen(self.port)

    def stop(self, event):
        """Remove callback(s) and template trackers."""
        # Only remove from_hub callback if it was registered
        if self.from_hub is not None:
            self.hub.remove_callback(self.join_change_callback)

        # Only remove tracker if it was created
        if self.tracker is not None:
            self.tracker.async_remove()

        self.hub.stop()

    async def join_change_callback(self, cbtype, value):
        """ Call service for tracked join change (from_hub)"""
        for join in self.from_hub:
            if cbtype == join[CONF_JOIN]:
                # For digital joins, ignore on>off transitions  (avoids double calls to service for momentary presses)
                if cbtype[:1] == "d" and value == "0":
                    pass
                else:
                    if CONF_SERVICE in join and CONF_SERVICE_DATA in join:
                        data = dict(join[CONF_SERVICE_DATA])
                        _LOGGER.debug(
                            f"join_change_callback calling service {join[CONF_SERVICE]} with data = {data} from join {cbtype} = {value}"
                        )
                        domain, service = join[CONF_SERVICE].split(".")
                        await self.hass.services.async_call(domain, service, data)
                    elif CONF_SCRIPT in join:
                        sequence = join[CONF_SCRIPT]
                        script = Script(
                            self.hass, sequence, "Crestron Join Change", DOMAIN
                        )
                        await script.async_run({"value": value}, self.context)
                        _LOGGER.debug(
                            f"join_change_callback calling script {join[CONF_SCRIPT]} from join {cbtype} = {value}"
                        )

    @callback
    def template_change_callback(self, event, updates):
        """ Set join from value_template (to_hub)"""
        # track_template_result = updates.pop()
        for track_template_result in updates:
            update_result = track_template_result.result
            update_template = track_template_result.template
            if update_result != "None":
                for join, template in self.to_hub.items():
                    if template == update_template:
                        _LOGGER.debug(
                            f"processing template_change_callback for join {join} with result {update_result}"
                        )
                        # Digital Join
                        if join[:1] == "d":
                            value = None
                            if update_result == STATE_ON or update_result == "True":
                                value = True
                            elif update_result == STATE_OFF or update_result == "False":
                                value = False
                            if value is not None:
                                _LOGGER.debug(
                                    f"template_change_callback setting digital join {int(join[1:])} to {value}"
                                )
                                self.hub.set_digital(int(join[1:]), value)
                        # Analog Join
                        if join[:1] == "a":
                            _LOGGER.debug(
                                f"template_change_callback setting analog join {int(join[1:])} to {int(update_result)}"
                            )
                            self.hub.set_analog(int(join[1:]), int(update_result))
                        # Serial Join
                        if join[:1] == "s":
                            _LOGGER.debug(
                                f"template_change_callback setting serial join {int(join[1:])} to {str(update_result)}"
                            )
                            self.hub.set_serial(int(join[1:]), str(update_result))

    async def sync_joins_to_hub(self):
        """Sync join values from HA to Crestron (only valid values)."""
        _LOGGER.debug("Syncing joins to control system")
        for join, template in self.to_hub.items():
            result = template.async_render()
            # Only sync joins that have valid template values (not "None")
            # This prevents sending zeros for uninitialized entities
            if result == "None":
                continue

            # Digital Join
            if join[:1] == "d":
                value = None
                if result == STATE_ON or result == "True":
                    value = True
                elif result == STATE_OFF or result == "False":
                    value = False
                if value is not None:
                    _LOGGER.debug(
                        f"sync_joins_to_hub setting digital join {int(join[1:])} to {value}"
                    )
                    self.hub.set_digital(int(join[1:]), value)
            # Analog Join
            elif join[:1] == "a":
                _LOGGER.debug(
                    f"sync_joins_to_hub setting analog join {int(join[1:])} to {int(result)}"
                )
                self.hub.set_analog(int(join[1:]), int(result))
            # Serial Join
            elif join[:1] == "s":
                _LOGGER.debug(
                    f"sync_joins_to_hub setting serial join {int(join[1:])} to {str(result)}"
                )
                self.hub.set_serial(int(join[1:]), str(result))

