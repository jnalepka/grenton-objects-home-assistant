"""
==================================================
Author: Jan Nalepka
Script version: 3.2
Date: 28.12.2025
Repository: https://github.com/jnalepka/grenton-objects-home-assistant
==================================================
"""

DOMAIN = 'grenton_objects'
CONF_API_ENDPOINT = 'api_endpoint'
CONF_GRENTON_ID = 'grenton_id'
CONF_GRENTON_TYPE = 'grenton_type'
CONF_GRENTON_TYPE_DOUT = 'DOUT'
CONF_GRENTON_TYPE_DIMMER = 'DIMMER'
CONF_GRENTON_TYPE_DALI = 'DALI'
CONF_GRENTON_TYPE_RGB = 'RGB'
CONF_GRENTON_TYPE_RGBW = 'RGB+W'
CONF_GRENTON_TYPE_LED_R = 'LED_R'
CONF_GRENTON_TYPE_LED_G = 'LED_G'
CONF_GRENTON_TYPE_LED_B = 'LED_B'
CONF_GRENTON_TYPE_LED_W = 'LED_W'
CONF_GRENTON_TYPE_DEFAULT_SENSOR = 'DEFAULT_SENSOR'
CONF_GRENTON_TYPE_MODBUS_RTU = 'MODBUS_RTU'
CONF_GRENTON_TYPE_MODBUS_VALUE = 'MODBUS_VALUE'
CONF_GRENTON_TYPE_MODBUS = 'MODBUS'
CONF_GRENTON_TYPE_MODBUS_CLIENT = 'MODBUS_CLIENT'
CONF_GRENTON_TYPE_MODBUS_SERVER = 'MODBUS_SERVER'
CONF_GRENTON_TYPE_MODBUS_SLAVE_RTU = 'MODBUS_SLAVE_RTU'
CONF_GRENTON_TYPE_RELAY_POWER = 'RELAY_POWER'
CONF_GRENTON_TYPE_ANALOG_SCALED_VALUE = 'ANALOG_SCALED_VALUE_OR_VALUE_%'
CONF_OBJECT_NAME = 'name'
CONF_REVERSED = 'reversed'
CONF_DEVICE_CLASS = 'device_class'
CONF_STATE_CLASS = 'state_class'
CONF_UNIT_OF_MEASUREMENT = 'unit_of_measurement'
CONF_AUTO_UPDATE = 'auto_update'
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 30  # sekundy

DEVICE_TYPE_OPTIONS = [
    "light",
    "switch",
    "cover",
    "climate",
    "sensor",
    "binary_sensor",
    "button"
]

DEVICE_CLASS_OPTIONS = [
    "apparent_power",
    "atmospheric_pressure",
    "battery",
    "carbon_dioxide",
    "carbon_monoxide",
    "current",
    "distance",
    "duration",
    "energy",
    "energy_storage",
    "frequency",
    "gas",
    "humidity",
    "illuminance",
    "irradiance",
    "moisture",
    "nitrogen_dioxide",
    "nitrogen_monoxide",
    "nitrous_oxide",
    "ozone",
    "ph",
    "pm1",
    "pm10",
    "pm25",
    "power",
    "power_factor",
    "precipitation",
    "precipitation_intensity",
    "pressure",
    "reactive_power",
    "signal_strength",
    "sound_pressure",
    "speed",
    "sulphur_dioxide",
    "temperature",
    "volatile_organic_compounds",
    "volatile_organic_compounds_parts",
    "voltage",
    "volume",
    "volume_flow_rate",
    "volume_storage",
    "water",
    "weight",
    "wind_speed"
]

STATE_CLASS_OPTIONS = [
    "measurement",
    "total",
    "total_increasing"
]

LIGHT_GRENTON_TYPE_OPTIONS = [
    CONF_GRENTON_TYPE_DOUT, 
    CONF_GRENTON_TYPE_DALI,
    CONF_GRENTON_TYPE_DIMMER, 
    CONF_GRENTON_TYPE_RGB, 
    CONF_GRENTON_TYPE_RGBW, 
    CONF_GRENTON_TYPE_LED_R, 
    CONF_GRENTON_TYPE_LED_G, 
    CONF_GRENTON_TYPE_LED_B, 
    CONF_GRENTON_TYPE_LED_W
]

SENSOR_GRENTON_TYPE_OPTIONS = [
    CONF_GRENTON_TYPE_DEFAULT_SENSOR, 
    CONF_GRENTON_TYPE_MODBUS_RTU, 
    CONF_GRENTON_TYPE_MODBUS_VALUE, 
    CONF_GRENTON_TYPE_MODBUS, 
    CONF_GRENTON_TYPE_MODBUS_CLIENT, 
    CONF_GRENTON_TYPE_MODBUS_SERVER, 
    CONF_GRENTON_TYPE_MODBUS_SLAVE_RTU,
    CONF_GRENTON_TYPE_RELAY_POWER,
    CONF_GRENTON_TYPE_ANALOG_SCALED_VALUE
]

LIGHT_GRENTON_TYPE_LED = [
    CONF_GRENTON_TYPE_LED_R, 
    CONF_GRENTON_TYPE_LED_G, 
    CONF_GRENTON_TYPE_LED_B, 
    CONF_GRENTON_TYPE_LED_W
]

LIGHT_GRENTON_TYPE_BRIGHTNESS = [
    CONF_GRENTON_TYPE_DALI,
    CONF_GRENTON_TYPE_DIMMER,
    CONF_GRENTON_TYPE_LED_R,
    CONF_GRENTON_TYPE_LED_G,
    CONF_GRENTON_TYPE_LED_B,
    CONF_GRENTON_TYPE_LED_W
]
