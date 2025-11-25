"""Platform for Crestron Thermostat integration (standard & floor-warming)."""

import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
)
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    FAN_ON,
    FAN_AUTO,
)
from homeassistant.const import CONF_NAME, CONF_TYPE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    HUB,
    DOMAIN,
    CONF_CLIMATES,
    # --- standard thermostat joins ---
    CONF_HEAT_SP_JOIN,
    CONF_COOL_SP_JOIN,
    CONF_REG_TEMP_JOIN,
    CONF_MODE_HEAT_JOIN,
    CONF_MODE_COOL_JOIN,
    CONF_MODE_AUTO_JOIN,
    CONF_MODE_OFF_JOIN,
    CONF_FAN_ON_JOIN,
    CONF_FAN_AUTO_JOIN,
    CONF_H1_JOIN,
    CONF_H2_JOIN,
    CONF_C1_JOIN,
    CONF_C2_JOIN,
    CONF_FA_JOIN,
    CONF_MODE_HEAT_COOL_JOIN,
    CONF_FAN_MODE_AUTO_JOIN,
    CONF_FAN_MODE_ON_JOIN,
    CONF_HVAC_ACTION_HEAT_JOIN,
    CONF_HVAC_ACTION_COOL_JOIN,
    CONF_HVAC_ACTION_IDLE_JOIN,
    # --- floor warming joins ---
    CONF_FLOOR_MODE_JOIN,
    CONF_FLOOR_MODE_FB_JOIN,
    CONF_FLOOR_SP_JOIN,
    CONF_FLOOR_SP_FB_JOIN,
    CONF_FLOOR_TEMP_JOIN,
)

_LOGGER = logging.getLogger(__name__)

# ----------------------------
# Schemas
# ----------------------------

STANDARD_CLIMATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_TYPE, default="standard"): vol.In(["standard", "floor_warming"]),
        vol.Required(CONF_HEAT_SP_JOIN): cv.positive_int,
        vol.Required(CONF_COOL_SP_JOIN): cv.positive_int,
        vol.Required(CONF_REG_TEMP_JOIN): cv.positive_int,
        vol.Required(CONF_MODE_HEAT_JOIN): cv.positive_int,
        vol.Required(CONF_MODE_COOL_JOIN): cv.positive_int,
        vol.Required(CONF_MODE_AUTO_JOIN): cv.positive_int,
        vol.Required(CONF_MODE_OFF_JOIN): cv.positive_int,
        vol.Required(CONF_FAN_ON_JOIN): cv.positive_int,
        vol.Required(CONF_FAN_AUTO_JOIN): cv.positive_int,
        vol.Required(CONF_H1_JOIN): cv.positive_int,
        vol.Optional(CONF_H2_JOIN): cv.positive_int,
        vol.Required(CONF_C1_JOIN): cv.positive_int,
        vol.Optional(CONF_C2_JOIN): cv.positive_int,
        vol.Required(CONF_FA_JOIN): cv.positive_int,
        vol.Required(CONF_MODE_HEAT_COOL_JOIN): cv.positive_int,
        vol.Required(CONF_FAN_MODE_AUTO_JOIN): cv.positive_int,
        vol.Required(CONF_FAN_MODE_ON_JOIN): cv.positive_int,
        vol.Required(CONF_HVAC_ACTION_HEAT_JOIN): cv.positive_int,
        vol.Required(CONF_HVAC_ACTION_COOL_JOIN): cv.positive_int,
        vol.Required(CONF_HVAC_ACTION_IDLE_JOIN): cv.positive_int,
    },
    extra=vol.ALLOW_EXTRA,
)

FLOOR_WARMING_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_TYPE, default="floor_warming"): vol.In(["standard", "floor_warming"]),
        vol.Required(CONF_FLOOR_MODE_JOIN): cv.positive_int,      # analog set (1/2)
        vol.Required(CONF_FLOOR_MODE_FB_JOIN): cv.positive_int,   # analog feedback (1/2)
        vol.Required(CONF_FLOOR_SP_JOIN): cv.positive_int,        # analog setpoint x10
        vol.Required(CONF_FLOOR_SP_FB_JOIN): cv.positive_int,     # analog setpoint feedback x10
        vol.Required(CONF_FLOOR_TEMP_JOIN): cv.positive_int,      # analog floor temp x10
    },
    extra=vol.ALLOW_EXTRA,
)

# Allow either a standard thermostat or a floor-warming thermostat
PLATFORM_SCHEMA = vol.Any(STANDARD_CLIMATE_SCHEMA, FLOOR_WARMING_SCHEMA)

# ----------------------------
# Setup
# ----------------------------

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    unit = hass.config.units.temperature_unit

    dev_type = config.get(CONF_TYPE, "standard")
    if dev_type == "floor_warming":
        entity = [CrestronFloorWarmingThermostat(hub, config, unit)]
    else:
        entity = [CrestronThermostat(hub, config, unit)]

    async_add_entities(entity)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Crestron climate devices from a config entry.

    Supports UI-configured climate entities (v1.13.0+).
    YAML platform setup (above) handles YAML-configured entities.
    """
    # Get hub from entry data
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if not entry_data:
        _LOGGER.warning("No entry data found for climate setup")
        return False

    hub_wrapper = entry_data.get('hub_wrapper')
    if not hub_wrapper:
        _LOGGER.warning("No hub_wrapper found for climate setup")
        return False

    # Get hub from wrapper
    hub = hub_wrapper.hub
    unit = hass.config.units.temperature_unit

    # Load climates from config entry (UI-configured)
    # v1.13.0: floor_warming type
    # v1.14.0: standard type
    climates_config = entry.data.get(CONF_CLIMATES, [])

    if climates_config:
        entities = []
        for climate_cfg in climates_config:
            dev_type = climate_cfg.get(CONF_TYPE, "standard")

            if dev_type == "floor_warming":
                # Parse floor warming joins (all analog)
                config = {
                    CONF_NAME: climate_cfg.get(CONF_NAME),
                    CONF_TYPE: "floor_warming",
                }

                # Parse analog join strings
                all_joins_valid = True
                for join_key in [CONF_FLOOR_MODE_JOIN, CONF_FLOOR_MODE_FB_JOIN,
                                CONF_FLOOR_SP_JOIN, CONF_FLOOR_SP_FB_JOIN, CONF_FLOOR_TEMP_JOIN]:
                    join_str = climate_cfg.get(join_key, "")
                    if join_str and join_str[0] == 'a' and join_str[1:].isdigit():
                        config[join_key] = int(join_str[1:])
                    else:
                        _LOGGER.error(
                            "Invalid join format for %s in %s: %s",
                            join_key, climate_cfg.get(CONF_NAME), join_str
                        )
                        all_joins_valid = False
                        break

                if all_joins_valid:
                    entities.append(CrestronFloorWarmingThermostat(hub, config, unit, from_ui=True))

            elif dev_type == "standard":
                # Parse standard thermostat joins (3 analog + 15-17 digital)
                config = {
                    CONF_NAME: climate_cfg.get(CONF_NAME),
                    CONF_TYPE: "standard",
                }

                # Parse analog joins (3 required)
                analog_joins = {
                    CONF_HEAT_SP_JOIN: climate_cfg.get(CONF_HEAT_SP_JOIN, ""),
                    CONF_COOL_SP_JOIN: climate_cfg.get(CONF_COOL_SP_JOIN, ""),
                    CONF_REG_TEMP_JOIN: climate_cfg.get(CONF_REG_TEMP_JOIN, ""),
                }

                all_joins_valid = True
                for join_key, join_str in analog_joins.items():
                    if join_str and join_str[0] == 'a' and join_str[1:].isdigit():
                        config[join_key] = int(join_str[1:])
                    else:
                        _LOGGER.error(
                            "Invalid analog join format for %s in %s: %s",
                            join_key, climate_cfg.get(CONF_NAME), join_str
                        )
                        all_joins_valid = False
                        break

                # Parse digital joins (15 required + 2 optional)
                digital_joins = {
                    CONF_MODE_HEAT_JOIN: climate_cfg.get(CONF_MODE_HEAT_JOIN, ""),
                    CONF_MODE_COOL_JOIN: climate_cfg.get(CONF_MODE_COOL_JOIN, ""),
                    CONF_MODE_AUTO_JOIN: climate_cfg.get(CONF_MODE_AUTO_JOIN, ""),
                    CONF_MODE_OFF_JOIN: climate_cfg.get(CONF_MODE_OFF_JOIN, ""),
                    CONF_FAN_ON_JOIN: climate_cfg.get(CONF_FAN_ON_JOIN, ""),
                    CONF_FAN_AUTO_JOIN: climate_cfg.get(CONF_FAN_AUTO_JOIN, ""),
                    CONF_H1_JOIN: climate_cfg.get(CONF_H1_JOIN, ""),
                    CONF_C1_JOIN: climate_cfg.get(CONF_C1_JOIN, ""),
                    CONF_FA_JOIN: climate_cfg.get(CONF_FA_JOIN, ""),
                    CONF_MODE_HEAT_COOL_JOIN: climate_cfg.get(CONF_MODE_HEAT_COOL_JOIN, ""),
                    CONF_FAN_MODE_AUTO_JOIN: climate_cfg.get(CONF_FAN_MODE_AUTO_JOIN, ""),
                    CONF_FAN_MODE_ON_JOIN: climate_cfg.get(CONF_FAN_MODE_ON_JOIN, ""),
                    CONF_HVAC_ACTION_HEAT_JOIN: climate_cfg.get(CONF_HVAC_ACTION_HEAT_JOIN, ""),
                    CONF_HVAC_ACTION_COOL_JOIN: climate_cfg.get(CONF_HVAC_ACTION_COOL_JOIN, ""),
                    CONF_HVAC_ACTION_IDLE_JOIN: climate_cfg.get(CONF_HVAC_ACTION_IDLE_JOIN, ""),
                }

                if all_joins_valid:
                    for join_key, join_str in digital_joins.items():
                        if join_str and join_str[0] == 'd' and join_str[1:].isdigit():
                            config[join_key] = int(join_str[1:])
                        else:
                            _LOGGER.error(
                                "Invalid digital join format for %s in %s: %s",
                                join_key, climate_cfg.get(CONF_NAME), join_str
                            )
                            all_joins_valid = False
                            break

                # Parse optional digital joins
                if all_joins_valid:
                    optional_joins = {
                        CONF_H2_JOIN: climate_cfg.get(CONF_H2_JOIN, ""),
                        CONF_C2_JOIN: climate_cfg.get(CONF_C2_JOIN, ""),
                    }
                    for join_key, join_str in optional_joins.items():
                        if join_str:  # Only parse if provided
                            if join_str[0] == 'd' and join_str[1:].isdigit():
                                config[join_key] = int(join_str[1:])
                            else:
                                _LOGGER.warning(
                                    "Invalid optional digital join format for %s in %s: %s (skipping)",
                                    join_key, climate_cfg.get(CONF_NAME), join_str
                                )

                if all_joins_valid:
                    entities.append(CrestronThermostat(hub, config, unit, from_ui=True))

        if entities:
            async_add_entities(entities)
            _LOGGER.info("Added %d UI-configured climate entities", len(entities))

    return True

# ----------------------------
# Standard HVAC Thermostat (unchanged functional logic)
# ----------------------------

class CrestronThermostat(ClimateEntity, RestoreEntity):
    def __init__(self, hub, config, unit, from_ui=False):
        self._hub = hub
        self._hvac_modes = [
            HVACMode.HEAT_COOL,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.OFF,
        ]
        self._fan_modes = [FAN_ON, FAN_AUTO]
        self._attr_supported_features = (
            ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._should_poll = False
        self._temperature_unit = unit
        self._from_ui = from_ui

        self._name = config.get(CONF_NAME, "Unnamed Thermostat")
        self._heat_sp_join = config.get(CONF_HEAT_SP_JOIN, 0)
        self._cool_sp_join = config.get(CONF_COOL_SP_JOIN, 0)
        self._reg_temp_join = config.get(CONF_REG_TEMP_JOIN, 0)
        self._mode_heat_join = config.get(CONF_MODE_HEAT_JOIN, 0)
        self._mode_cool_join = config.get(CONF_MODE_COOL_JOIN, 0)
        self._mode_auto_join = config.get(CONF_MODE_AUTO_JOIN, 0)
        self._mode_off_join = config.get(CONF_MODE_OFF_JOIN, 0)
        self._fan_on_join = config.get(CONF_FAN_ON_JOIN, 0)
        self._fan_auto_join = config.get(CONF_FAN_AUTO_JOIN, 0)
        self._h1_join = config.get(CONF_H1_JOIN, 0)
        self._h2_join = config.get(CONF_H2_JOIN, 0)
        self._c1_join = config.get(CONF_C1_JOIN, 0)
        self._c2_join = config.get(CONF_C2_JOIN, 0)
        self._fa_join = config.get(CONF_FA_JOIN, 0)
        self._mode_heat_cool_join = config.get(CONF_MODE_HEAT_COOL_JOIN, 0)
        self._fan_mode_auto_join = config.get(CONF_FAN_MODE_AUTO_JOIN, 0)
        self._fan_mode_on_join = config.get(CONF_FAN_MODE_ON_JOIN, 0)
        self._hvac_action_heat_join = config.get(CONF_HVAC_ACTION_HEAT_JOIN, 0)
        self._hvac_action_cool_join = config.get(CONF_HVAC_ACTION_COOL_JOIN, 0)
        self._hvac_action_idle_join = config.get(CONF_HVAC_ACTION_IDLE_JOIN, 0)

        # State restoration variables
        self._restored_hvac_mode = None
        self._restored_fan_mode = None
        self._restored_temp_low = None
        self._restored_temp_high = None
        self._restored_current_temp = None

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._hub.register_callback(self.process_callback)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            # Only restore valid HVAC modes, not "unavailable" or "unknown"
            if last_state.state not in (None, "unavailable", "unknown"):
                try:
                    # Validate it's a valid HVACMode
                    self._restored_hvac_mode = HVACMode(last_state.state)
                except ValueError:
                    _LOGGER.warning("Invalid HVAC mode in restored state: %s", last_state.state)
                    self._restored_hvac_mode = None

            self._restored_fan_mode = last_state.attributes.get('fan_mode')
            self._restored_temp_low = last_state.attributes.get('target_temp_low')
            self._restored_temp_high = last_state.attributes.get('target_temp_high')
            self._restored_current_temp = last_state.attributes.get('current_temperature')
            _LOGGER.debug(
                "Restored %s: mode=%s, fan=%s, temps=%s/%s",
                self.name, self._restored_hvac_mode, self._restored_fan_mode,
                self._restored_temp_low, self._restored_temp_high
            )

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype, value):
        # Only update if this is one of our joins or connection state changed
        if cbtype == "available":
            self.async_write_ha_state()
            return

        # Build set of relevant joins for standard thermostat
        relevant_joins = {
            f"a{self._heat_sp_join}",
            f"a{self._cool_sp_join}",
            f"a{self._reg_temp_join}",
            f"d{self._mode_heat_join}",
            f"d{self._mode_cool_join}",
            f"d{self._mode_auto_join}",
            f"d{self._mode_off_join}",
            f"d{self._fan_on_join}",
            f"d{self._fan_auto_join}",
            f"d{self._h1_join}",
            f"d{self._c1_join}",
            f"d{self._fa_join}",
        }
        # Add optional joins if configured
        if self._h2_join:
            relevant_joins.add(f"d{self._h2_join}")
        if self._c2_join:
            relevant_joins.add(f"d{self._c2_join}")

        if cbtype in relevant_joins:
            self.async_write_ha_state()

    @property
    def available(self):
        return self._hub.is_available()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """Return unique ID for this entity."""
        # Use heat setpoint join as primary identifier
        if self._from_ui:
            return f"crestron_climate_ui_a{self._heat_sp_join}"
        return f"crestron_climate_a{self._heat_sp_join}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"crestron_{self._hub.port}")},
            name="Crestron Control System",
            manufacturer="Crestron Electronics",
            model="XSIG Gateway",
            sw_version="1.6.0",
        )

    @property
    def hvac_modes(self):
        return self._hvac_modes

    @property
    def fan_modes(self):
        return self._fan_modes

    @property
    def supported_features(self):
        return self._attr_supported_features

    @property
    def should_poll(self):
        return self._should_poll

    @property
    def temperature_unit(self):
        return self._temperature_unit

    @property
    def current_temperature(self):
        """Return the current temperature."""
        if self._hub.has_analog_value(self._reg_temp_join):
            return self._hub.get_analog(self._reg_temp_join) / 10
        return self._restored_current_temp

    @property
    def target_temperature_high(self):
        """Return the high target temperature."""
        if self._hub.has_analog_value(self._cool_sp_join):
            return self._hub.get_analog(self._cool_sp_join) / 10
        return self._restored_temp_high

    @property
    def target_temperature_low(self):
        """Return the low target temperature."""
        if self._hub.has_analog_value(self._heat_sp_join):
            return self._hub.get_analog(self._heat_sp_join) / 10
        return self._restored_temp_low

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        # Use real values from Crestron if available
        if self._hub.has_digital_value(self._mode_auto_join):
            if self._hub.get_digital(self._mode_auto_join):
                return HVACMode.HEAT_COOL
        if self._hub.has_digital_value(self._mode_heat_join):
            if self._hub.get_digital(self._mode_heat_join):
                return HVACMode.HEAT
        if self._hub.has_digital_value(self._mode_cool_join):
            if self._hub.get_digital(self._mode_cool_join):
                return HVACMode.COOL
        if self._hub.has_digital_value(self._mode_off_join):
            if self._hub.get_digital(self._mode_off_join):
                return HVACMode.OFF
        # Use restored mode if available
        return self._restored_hvac_mode

    @property
    def fan_mode(self):
        """Return the current fan mode."""
        # Use real values from Crestron if available
        if self._hub.has_digital_value(self._fan_auto_join):
            if self._hub.get_digital(self._fan_auto_join):
                return FAN_AUTO
        if self._hub.has_digital_value(self._fan_on_join):
            if self._hub.get_digital(self._fan_on_join):
                return FAN_ON
        # Use restored fan mode if available
        return self._restored_fan_mode

    @property
    def hvac_action(self):
        if self._hub.get_digital(self._h1_join) or self._hub.get_digital(self._h2_join):
            return HVACAction.HEATING
        elif self._hub.get_digital(self._c1_join) or self._hub.get_digital(self._c2_join):
            return HVACAction.COOLING
        else:
            return HVACAction.IDLE

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.HEAT_COOL:
            self._hub.set_digital(self._mode_cool_join, False)
            self._hub.set_digital(self._mode_off_join, False)
            self._hub.set_digital(self._mode_heat_join, False)
            self._hub.set_digital(self._mode_auto_join, True)
        if hvac_mode == HVACMode.HEAT:
            self._hub.set_digital(self._mode_auto_join, False)
            self._hub.set_digital(self._mode_cool_join, False)
            self._hub.set_digital(self._mode_off_join, False)
            self._hub.set_digital(self._mode_heat_join, True)
        if hvac_mode == HVACMode.COOL:
            self._hub.set_digital(self._mode_auto_join, False)
            self._hub.set_digital(self._mode_off_join, False)
            self._hub.set_digital(self._mode_heat_join, False)
            self._hub.set_digital(self._mode_cool_join, True)
        if hvac_mode == HVACMode.OFF:
            self._hub.set_digital(self._mode_auto_join, False)
            self._hub.set_digital(self._mode_cool_join, False)
            self._hub.set_digital(self._mode_heat_join, False)
            self._hub.set_digital(self._mode_off_join, True)

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode == FAN_AUTO:
            self._hub.set_digital(self._fan_on_join, False)
            self._hub.set_digital(self._fan_auto_join, True)
        if fan_mode == FAN_ON:
            self._hub.set_digital(self._fan_auto_join, False)
            self._hub.set_digital(self._fan_on_join, True)

    async def async_set_temperature(self, **kwargs):
        """Set target temperatures."""
        await self._hub.async_set_analog(self._heat_sp_join, int(round(kwargs["target_temp_low"] * 10)))
        await self._hub.async_set_analog(self._cool_sp_join, int(round(kwargs["target_temp_high"] * 10)))

# ----------------------------
# Floor-Warming Thermostat
# ----------------------------

class CrestronFloorWarmingThermostat(ClimateEntity, RestoreEntity):
    """Floor-warming-only thermostat: Off/Heat modes, single setpoint, floor temp readback."""

    def __init__(self, hub, config, unit, from_ui=False):
        self._hub = hub
        self._temperature_unit = unit
        self._should_poll = False
        self._from_ui = from_ui
        self._name = config.get(CONF_NAME, "Floor Warming")

        # joins (all analog)
        self._mode_join = config.get(CONF_FLOOR_MODE_JOIN)
        self._mode_fb_join = config.get(CONF_FLOOR_MODE_FB_JOIN)
        self._sp_join = config.get(CONF_FLOOR_SP_JOIN)
        self._sp_fb_join = config.get(CONF_FLOOR_SP_FB_JOIN)
        self._temp_join = config.get(CONF_FLOOR_TEMP_JOIN)

        self._hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

        # State restoration variables
        self._restored_hvac_mode = None
        self._restored_target_temp = None
        self._restored_current_temp = None

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        self._hub.register_callback(self.process_callback)

        # Restore last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            # Only restore valid HVAC modes, not "unavailable" or "unknown"
            if last_state.state not in (None, "unavailable", "unknown"):
                try:
                    # Validate it's a valid HVACMode
                    self._restored_hvac_mode = HVACMode(last_state.state)
                except ValueError:
                    _LOGGER.warning("Invalid HVAC mode in restored state: %s", last_state.state)
                    self._restored_hvac_mode = None

            self._restored_target_temp = last_state.attributes.get('temperature')
            self._restored_current_temp = last_state.attributes.get('current_temperature')
            _LOGGER.debug(
                "Restored %s: mode=%s, target=%s, current=%s",
                self.name, self._restored_hvac_mode, self._restored_target_temp,
                self._restored_current_temp
            )

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype, value):
        # Only update if this is one of our joins or connection state changed
        if cbtype == "available":
            self.async_write_ha_state()
            return

        # Build set of relevant joins for floor warming thermostat (all analog)
        relevant_joins = {
            f"a{self._mode_join}",
            f"a{self._mode_fb_join}",
            f"a{self._sp_join}",
            f"a{self._sp_fb_join}",
            f"a{self._temp_join}",
        }

        if cbtype in relevant_joins:
            self.async_write_ha_state()

    # ----- standard props -----

    @property
    def available(self):
        return self._hub.is_available()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        """Return unique ID for this entity."""
        # Use setpoint join as primary identifier
        if self._from_ui:
            return f"crestron_climate_ui_a{self._sp_join}"
        return f"crestron_climate_a{self._sp_join}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"crestron_{self._hub.port}")},
            name="Crestron Control System",
            manufacturer="Crestron Electronics",
            model="XSIG Gateway",
            sw_version="1.6.0",
        )

    @property
    def should_poll(self):
        return self._should_poll

    @property
    def temperature_unit(self):
        return self._temperature_unit

    @property
    def hvac_modes(self):
        return self._hvac_modes

    @property
    def supported_features(self):
        return self._attr_supported_features

    # ----- temperatures -----

    @property
    def current_temperature(self):
        """Return the current floor temperature."""
        if self._hub.has_analog_value(self._temp_join):
            return self._hub.get_analog(self._temp_join) / 10
        return self._restored_current_temp

    @property
    def target_temperature(self):
        """Return the target temperature."""
        if self._hub.has_analog_value(self._sp_fb_join):
            return self._hub.get_analog(self._sp_fb_join) / 10
        return self._restored_target_temp

    # ----- modes & action -----

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        if self._hub.has_analog_value(self._mode_fb_join):
            mode_val = self._hub.get_analog(self._mode_fb_join)
            if mode_val == 2:
                return HVACMode.HEAT
            return HVACMode.OFF
        # Use restored mode if available
        return self._restored_hvac_mode

    @property
    def hvac_action(self):
        # No explicit heating-action join; infer:
        # If in HEAT and floor temp is below setpoint (by small hysteresis), assume HEATING else IDLE
        if self.hvac_mode == HVACMode.HEAT:
            try:
                if (self.target_temperature - self.current_temperature) > 0.2:
                    return HVACAction.HEATING
            except Exception:  # if any value missing
                pass
            return HVACAction.IDLE
        return HVACAction.IDLE

    # ----- setters -----

    async def async_set_hvac_mode(self, hvac_mode):
        # analog: 1 = Off, 2 = Heat
        if hvac_mode == HVACMode.HEAT:
            await self._hub.async_set_analog(self._mode_join, 2)
        elif hvac_mode == HVACMode.OFF:
            await self._hub.async_set_analog(self._mode_join, 1)

    async def async_turn_on(self):
        await self._hub.async_set_analog(self._mode_join, 2)

    async def async_turn_off(self):
        await self._hub.async_set_analog(self._mode_join, 1)

    async def async_set_temperature(self, **kwargs):
        # Expect "temperature" in kwargs; write tenths
        if "temperature" in kwargs:
            await self._hub.async_set_analog(self._sp_join, int(round(kwargs["temperature"] * 10)))
