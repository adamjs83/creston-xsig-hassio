VERSION = "1.24.6"
HUB = "hub"
DOMAIN = "crestron"
CONF_PORT = "port"
CONF_TO_HUB = "to_joins"
CONF_FROM_HUB = "from_joins"
CONF_JOIN = "join"
CONF_SCRIPT = "script"
CONF_IS_ON_JOIN = "is_on_join"
CONF_HEAT_SP_JOIN = "heat_sp_join"
CONF_COOL_SP_JOIN = "cool_sp_join"
CONF_REG_TEMP_JOIN = "reg_temp_join"
CONF_MODE_HEAT_JOIN = "mode_heat_join"
CONF_MODE_COOL_JOIN = "mode_cool_join"
CONF_MODE_AUTO_JOIN = "mode_auto_join"
CONF_MODE_OFF_JOIN = "mode_off_join"
CONF_FAN_ON_JOIN = "fan_on_join"
CONF_FAN_AUTO_JOIN = "fan_auto_join"
CONF_H1_JOIN = "h1_join"
CONF_H2_JOIN = "h2_join"
CONF_C1_JOIN = "c1_join"
CONF_C2_JOIN = "c2_join"
CONF_FA_JOIN = "fa_join"
CONF_IS_OPENING_JOIN = "is_opening_join"
CONF_IS_CLOSING_JOIN = "is_closing_join"
CONF_IS_CLOSED_JOIN = "is_closed_join"
CONF_STOP_JOIN = "stop_join"
CONF_POS_JOIN = "pos_join"
CONF_BRIGHTNESS_JOIN = "brightness_join"
CONF_MUTE_JOIN = "mute_join"
CONF_VOLUME_JOIN = "volume_join"
CONF_SOURCE_NUM_JOIN = "source_number_join"
CONF_SOURCES = "sources"
CONF_VALUE_JOIN = "value_join"
CONF_DIVISOR = "divisor"
CONF_SWITCH_JOIN = "switch_join"

# Media player constants (v1.19.0+)
CONF_POWER_ON_JOIN = "power_on_join"
CONF_POWER_OFF_JOIN = "power_off_join"
CONF_PLAY_JOIN = "play_join"
CONF_PAUSE_JOIN = "pause_join"
# Note: CONF_STOP_JOIN defined above (line 26) - used by both covers and media players
CONF_NEXT_JOIN = "next_join"
CONF_PREVIOUS_JOIN = "previous_join"
CONF_REPEAT_JOIN = "repeat_join"
CONF_SHUFFLE_JOIN = "shuffle_join"

# Entity storage (v1.8.0+)
CONF_COVERS = "covers"
CONF_BINARY_SENSORS = "binary_sensors"
CONF_SENSORS = "sensors"
CONF_LIGHTS = "lights"
CONF_SWITCHES = "switches"
CONF_CLIMATES = "climates"
CONF_DIMMERS = "dimmers"
CONF_MEDIA_PLAYERS = "media_players"

# LED Binding configuration (v1.22.0+)
CONF_LED_BINDINGS = "led_bindings"  # Stored in config_entry.options
CONF_INVERT = "invert"

# Climate additional constants
CONF_MODE_HEAT_COOL_JOIN = "mode_heat_cool_join"
CONF_FAN_MODE_AUTO_JOIN = "fan_mode_auto_join"
CONF_FAN_MODE_ON_JOIN = "fan_mode_on_join"
CONF_HVAC_ACTION_HEAT_JOIN = "hvac_action_heat_join"
CONF_HVAC_ACTION_COOL_JOIN = "hvac_action_cool_join"
CONF_HVAC_ACTION_IDLE_JOIN = "hvac_action_idle_join"

# Floor warming thermostat constants (new)
CONF_FLOOR_MODE_JOIN = "floor_mode_join"           # analog set: 1=Off, 2=Heat
CONF_FLOOR_MODE_FB_JOIN = "floor_mode_fb_join"     # analog feedback: 1/2
CONF_FLOOR_SP_JOIN = "floor_sp_join"               # analog setpoint (tenths)
CONF_FLOOR_SP_FB_JOIN = "floor_sp_fb_join"         # analog setpoint feedback (tenths)
CONF_FLOOR_TEMP_JOIN = "floor_temp_join"           # analog floor temperature (tenths)

# Dimmer/Keypad constants (v1.15.0+)
CONF_LIGHTING_LOAD = "lighting_load"
CONF_BUTTON_COUNT = "button_count"
CONF_BUTTONS = "buttons"
CONF_PRESS = "press"
CONF_DOUBLE_PRESS = "double_press"
CONF_HOLD = "hold"
CONF_FEEDBACK = "feedback"
CONF_ACTION = "action"
CONF_SERVICE_DATA = "service_data"

# Domain action mappings for dimmer buttons (v1.16.x - deprecated)
DOMAIN_ACTIONS = {
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
DEVICE_TYPE_DIMMER_KEYPAD = "dimmer_keypad"
CONF_BASE_JOIN = "base_join"
CONF_HAS_LIGHTING_LOAD = "has_lighting_load"
CONF_LIGHT_ON_JOIN = "light_on_join"
CONF_LIGHT_BRIGHTNESS_JOIN = "light_brightness_join"

# Entity types for dimmer/keypad
ENTITY_TYPE_BUTTON_EVENT = "button_event"
ENTITY_TYPE_BUTTON_LED = "button_led"
ENTITY_TYPE_LED_BINDING = "led_binding"
ENTITY_TYPE_DIMMER_LIGHT = "dimmer_light"

# LED Binding: Bindable entity domains (v1.17.0+)
# These domains can be bound to LED switches for state feedback
BINDABLE_DOMAINS = {
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
STATE_TO_LED = {
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
