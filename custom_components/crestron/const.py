VERSION: str = "1.24.9"
HUB: str = "hub"
DOMAIN: str = "crestron"
CONF_PORT: str = "port"
CONF_TO_HUB: str = "to_joins"
CONF_FROM_HUB: str = "from_joins"
CONF_JOIN: str = "join"
CONF_SCRIPT: str = "script"
CONF_IS_ON_JOIN: str = "is_on_join"
CONF_HEAT_SP_JOIN: str = "heat_sp_join"
CONF_COOL_SP_JOIN: str = "cool_sp_join"
CONF_REG_TEMP_JOIN: str = "reg_temp_join"
CONF_MODE_HEAT_JOIN: str = "mode_heat_join"
CONF_MODE_COOL_JOIN: str = "mode_cool_join"
CONF_MODE_AUTO_JOIN: str = "mode_auto_join"
CONF_MODE_OFF_JOIN: str = "mode_off_join"
CONF_FAN_ON_JOIN: str = "fan_on_join"
CONF_FAN_AUTO_JOIN: str = "fan_auto_join"
CONF_H1_JOIN: str = "h1_join"
CONF_H2_JOIN: str = "h2_join"
CONF_C1_JOIN: str = "c1_join"
CONF_C2_JOIN: str = "c2_join"
CONF_FA_JOIN: str = "fa_join"
CONF_IS_OPENING_JOIN: str = "is_opening_join"
CONF_IS_CLOSING_JOIN: str = "is_closing_join"
CONF_IS_CLOSED_JOIN: str = "is_closed_join"
CONF_STOP_JOIN: str = "stop_join"
CONF_POS_JOIN: str = "pos_join"
CONF_BRIGHTNESS_JOIN: str = "brightness_join"
CONF_MUTE_JOIN: str = "mute_join"
CONF_VOLUME_JOIN: str = "volume_join"
CONF_SOURCE_NUM_JOIN: str = "source_number_join"
CONF_SOURCES: str = "sources"
CONF_VALUE_JOIN: str = "value_join"
CONF_DIVISOR: str = "divisor"
CONF_SWITCH_JOIN: str = "switch_join"

# Media player constants (v1.19.0+)
CONF_POWER_ON_JOIN: str = "power_on_join"
CONF_POWER_OFF_JOIN: str = "power_off_join"
CONF_PLAY_JOIN: str = "play_join"
CONF_PAUSE_JOIN: str = "pause_join"
# Note: CONF_STOP_JOIN defined above (line 26) - used by both covers and media players
CONF_NEXT_JOIN: str = "next_join"
CONF_PREVIOUS_JOIN: str = "previous_join"
CONF_REPEAT_JOIN: str = "repeat_join"
CONF_SHUFFLE_JOIN: str = "shuffle_join"

# Entity storage (v1.8.0+)
CONF_COVERS: str = "covers"
CONF_BINARY_SENSORS: str = "binary_sensors"
CONF_SENSORS: str = "sensors"
CONF_LIGHTS: str = "lights"
CONF_SWITCHES: str = "switches"
CONF_CLIMATES: str = "climates"
CONF_DIMMERS: str = "dimmers"
CONF_MEDIA_PLAYERS: str = "media_players"

# LED Binding configuration (v1.22.0+)
CONF_LED_BINDINGS: str = "led_bindings"  # Stored in config_entry.options
CONF_INVERT: str = "invert"

# Climate additional constants
CONF_MODE_HEAT_COOL_JOIN: str = "mode_heat_cool_join"
CONF_FAN_MODE_AUTO_JOIN: str = "fan_mode_auto_join"
CONF_FAN_MODE_ON_JOIN: str = "fan_mode_on_join"
CONF_HVAC_ACTION_HEAT_JOIN: str = "hvac_action_heat_join"
CONF_HVAC_ACTION_COOL_JOIN: str = "hvac_action_cool_join"
CONF_HVAC_ACTION_IDLE_JOIN: str = "hvac_action_idle_join"

# Floor warming thermostat constants (new)
CONF_FLOOR_MODE_JOIN: str = "floor_mode_join"           # analog set: 1=Off, 2=Heat
CONF_FLOOR_MODE_FB_JOIN: str = "floor_mode_fb_join"     # analog feedback: 1/2
CONF_FLOOR_SP_JOIN: str = "floor_sp_join"               # analog setpoint (tenths)
CONF_FLOOR_SP_FB_JOIN: str = "floor_sp_fb_join"         # analog setpoint feedback (tenths)
CONF_FLOOR_TEMP_JOIN: str = "floor_temp_join"           # analog floor temperature (tenths)

# Dimmer/Keypad constants (v1.15.0+)
CONF_LIGHTING_LOAD: str = "lighting_load"
CONF_BUTTON_COUNT: str = "button_count"
CONF_BUTTONS: str = "buttons"
CONF_PRESS: str = "press"
CONF_DOUBLE_PRESS: str = "double_press"
CONF_HOLD: str = "hold"
CONF_FEEDBACK: str = "feedback"
CONF_ACTION: str = "action"
CONF_SERVICE_DATA: str = "service_data"

# Domain action mappings for dimmer buttons (v1.16.x - deprecated)
DOMAIN_ACTIONS: dict[str, list[str]] = {
    "light": ["turn_on", "turn_off", "toggle"],
    "switch": ["turn_on", "turn_off", "toggle"],
    "cover": ["open_cover", "close_cover", "stop_cover", "toggle"],
    "scene": ["turn_on"],
    "script": ["turn_on"],
    "climate": ["turn_on", "turn_off", "set_temperature", "set_hvac_mode"],
    "media_player": ["turn_on", "turn_off", "media_play", "media_pause", "media_play_pause", "volume_up", "volume_down", "volume_mute"],
    "fan": ["turn_on", "turn_off", "toggle", "increase_speed", "decrease_speed"],
    "lock": ["lock", "unlock"],
    "vacuum": ["start", "stop", "return_to_base"],
    "input_boolean": ["turn_on", "turn_off", "toggle"],
    "automation": ["turn_on", "turn_off", "toggle", "trigger"],
    "group": ["turn_on", "turn_off", "toggle"],
}

# Dimmer/Keypad Device Types (v1.17.0+)
DEVICE_TYPE_DIMMER_KEYPAD: str = "dimmer_keypad"
CONF_BASE_JOIN: str = "base_join"
CONF_HAS_LIGHTING_LOAD: str = "has_lighting_load"
CONF_LIGHT_ON_JOIN: str = "light_on_join"
CONF_LIGHT_BRIGHTNESS_JOIN: str = "light_brightness_join"

# Entity types for dimmer/keypad
ENTITY_TYPE_BUTTON_EVENT: str = "button_event"
ENTITY_TYPE_BUTTON_LED: str = "button_led"
ENTITY_TYPE_LED_BINDING: str = "led_binding"
ENTITY_TYPE_DIMMER_LIGHT: str = "dimmer_light"

# LED Binding: Bindable entity domains (v1.17.0+)
# These domains can be bound to LED switches for state feedback
BINDABLE_DOMAINS: dict[str, list[str]] = {
    "light": ["on", "off"],
    "switch": ["on", "off"],
    "binary_sensor": ["on", "off"],
    "lock": ["locked", "unlocked"],
    "cover": ["open", "closed", "opening", "closing"],
    "media_player": ["playing", "paused", "idle", "off"],
    "climate": ["heat", "cool", "heat_cool", "auto", "off"],
    "fan": ["on", "off"],
    "input_boolean": ["on", "off"],
    "automation": ["on", "off"],
    "vacuum": ["cleaning", "docked", "paused", "idle", "returning"],
    "alarm_control_panel": ["armed_away", "armed_home", "armed_night", "disarmed"],
    "person": ["home", "not_home"],
    "device_tracker": ["home", "not_home"],
    "sun": ["above_horizon", "below_horizon"],
}

# LED Binding: State to LED on/off mapping (v1.17.0+)
# Maps entity states to LED on (True) or off (False)
STATE_TO_LED: dict[str, bool] = {
    # Common states
    "on": True,
    "off": False,
    "true": True,
    "false": False,

    # Lock states
    "locked": True,
    "unlocked": False,
    "locking": True,
    "unlocking": False,

    # Cover states
    "open": True,
    "closed": False,
    "opening": True,
    "closing": True,

    # Media player states
    "playing": True,
    "paused": False,
    "idle": False,

    # Climate states
    "heat": True,
    "cool": True,
    "heat_cool": True,
    "auto": True,

    # Vacuum states
    "cleaning": True,
    "docked": False,
    "returning": True,

    # Alarm states
    "armed_away": True,
    "armed_home": True,
    "armed_night": True,
    "disarmed": False,

    # Presence states
    "home": True,
    "not_home": False,

    # Sun states
    "above_horizon": True,
    "below_horizon": False,
}
