"""
==================================================
Author: Jan Nalepka
Script version: 3.4
Date: 29.12.2025
Repository: https://github.com/jnalepka/grenton-objects-home-assistant
==================================================
"""

import aiohttp
from .const import (
    CONF_API_ENDPOINT,
    CONF_GRENTON_ID,
    CONF_OBJECT_NAME,
    CONF_GRENTON_TYPE,
    CONF_GRENTON_TYPE_DIMMER,
    CONF_GRENTON_TYPE_RGB,
    CONF_GRENTON_TYPE_RGBW,
    CONF_GRENTON_TYPE_DOUT,
    CONF_GRENTON_TYPE_LED_R,
    CONF_GRENTON_TYPE_LED_G,
    CONF_GRENTON_TYPE_LED_B,
    CONF_GRENTON_TYPE_LED_W,
    CONF_AUTO_UPDATE,
    CONF_UPDATE_INTERVAL, 
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LIGHT_GRENTON_TYPE_LED,
    LIGHT_GRENTON_TYPE_BRIGHTNESS
)
from .api import get_api_client, GrentonApiError
from .mixins import GrentonPollingMixin, is_within_debounce
import logging
import voluptuous as vol
from homeassistant.components.light import (
    LightEntity, 
    PLATFORM_SCHEMA, 
    ColorMode
)
from homeassistant.const import (STATE_ON, STATE_OFF)
from homeassistant.util import color as color_util

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_ENDPOINT): str,
    vol.Required(CONF_GRENTON_ID): str,
    vol.Required(CONF_GRENTON_TYPE, default=CONF_GRENTON_TYPE_DOUT): str, #DOUT, DIMMER, RGB, RGBW, LED_R, LED_G, LED_B, LED_W
    vol.Optional(CONF_OBJECT_NAME, default='Grenton Light'): str
})

async def async_setup_entry(hass, config_entry, async_add_entities):
    api_endpoint = config_entry.options.get(CONF_API_ENDPOINT, config_entry.data.get(CONF_API_ENDPOINT))
    grenton_id = config_entry.data.get(CONF_GRENTON_ID)
    grenton_type = config_entry.options.get(CONF_GRENTON_TYPE, config_entry.data.get(CONF_GRENTON_TYPE, CONF_GRENTON_TYPE_DOUT))
    object_name = config_entry.data.get(CONF_OBJECT_NAME, "Grenton Light")
    auto_update = config_entry.options.get(CONF_AUTO_UPDATE, config_entry.data.get(CONF_AUTO_UPDATE, True))
    update_interval = config_entry.options.get(CONF_UPDATE_INTERVAL, config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    
    api_client = get_api_client(hass, api_endpoint)
    entity = GrentonLight(api_endpoint, grenton_id, grenton_type, object_name, auto_update, update_interval, api_client)
    async_add_entities([entity], True)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entities": {}}

    hass.data[DOMAIN]["entities"][entity.entity_id] = entity

class GrentonLight(GrentonPollingMixin, LightEntity):
    def __init__(self, api_endpoint, grenton_id, grenton_type, object_name, auto_update, update_interval, api_client):
        self._grenton_id = grenton_id
        self._api_endpoint = api_endpoint
        self._grenton_type = grenton_type
        self._object_name = object_name
        self._api_client = api_client
        self._state = None
        self._supported_color_modes: set[ColorMode | str] = set()
        self._brightness = None
        self._last_brightness = None
        self._rgb_color = None
        self._white = None
        self._last_command_time = None
        self._auto_update = auto_update
        self._update_interval = update_interval
        self._unsub_interval = None
        self._initialized = False
        
        grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
        
        if self._grenton_type in LIGHT_GRENTON_TYPE_LED:
            self._unique_id = f"grenton_{grenton_id_part_1}_{grenton_type}"
        else:
            self._unique_id = f"grenton_{grenton_id_part_1}"
        
        if self._grenton_type in LIGHT_GRENTON_TYPE_BRIGHTNESS:
            self._supported_color_modes.add(ColorMode.BRIGHTNESS)
        elif self._grenton_type == CONF_GRENTON_TYPE_RGB:
            self._supported_color_modes.add(ColorMode.RGB)
        elif self._grenton_type == CONF_GRENTON_TYPE_RGBW:
            self._supported_color_modes = {
                ColorMode.RGB,
                ColorMode.WHITE,
            }
            self._color_mode = ColorMode.RGB
        else:
            self._supported_color_modes.add(ColorMode.ONOFF)

    async def async_force_state(self, state: int):
        self._state = STATE_ON if state == 1 else STATE_OFF
        self.async_write_ha_state()

    async def async_force_brightness(self, brightness: float):
        self._state = STATE_OFF if brightness == 0 else STATE_ON
        grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
        if self._grenton_type == CONF_GRENTON_TYPE_RGB or self._grenton_type == CONF_GRENTON_TYPE_DIMMER:
            if self._grenton_type == CONF_GRENTON_TYPE_DIMMER and grenton_id_part_1.startswith("ZWA"):
                self._brightness = brightness
                self._last_brightness = brightness
            else:
                self._brightness = brightness * 255
                self._last_brightness = brightness * 255
        elif self._grenton_type == CONF_GRENTON_TYPE_LED_R or self._grenton_type == CONF_GRENTON_TYPE_LED_G or self._grenton_type == CONF_GRENTON_TYPE_LED_B or self._grenton_type == CONF_GRENTON_TYPE_LED_W:
            self._brightness = brightness
            self._last_brightness = brightness
        self.async_write_ha_state()

    async def async_force_rgb(self, hex: str):
        self._rgb_color = color_util.rgb_hex_to_rgb_list(hex.strip("#"))
        self.async_write_ha_state()

    async def async_force_rgbw(self, hex: str, brightness: float, white: float):
        if white > 0:
            self._state = STATE_ON
            self._color_mode = ColorMode.WHITE
            self._white = white
            self._brightness = white
            self._last_brightness = white
        elif hex != "#000000":
            self._state = STATE_ON
            self._color_mode = ColorMode.RGB
            self._rgb_color = color_util.rgb_hex_to_rgb_list(hex.strip("#"))
            self._brightness = brightness * 255
            self._last_brightness = brightness * 255
        else:
            self._state = STATE_OFF
        self.async_write_ha_state()

    @property
    def name(self):
        return self._object_name

    @property
    def is_on(self):
        return self._state == STATE_ON

    @property
    def supported_color_modes(self):
        return self._supported_color_modes
    
    @property
    def color_mode(self) -> ColorMode:
        if self._grenton_type in LIGHT_GRENTON_TYPE_BRIGHTNESS:
            return ColorMode.BRIGHTNESS
        elif self._grenton_type == CONF_GRENTON_TYPE_RGB:
            return ColorMode.RGB
        elif self._grenton_type == CONF_GRENTON_TYPE_RGBW:
            if self._color_mode in (ColorMode.RGB, ColorMode.WHITE):
                return self._color_mode
            return ColorMode.RGB
        else:
            return ColorMode.ONOFF

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def brightness(self):
        return self._brightness

    @property
    def rgb_color(self):
        return self._rgb_color

    @property
    def white(self):
        return self._white
    
    @property
    def should_poll(self):
        return False
        
    def _generate_command(self, command_type, grenton_id_part_0, grenton_id_part_1, action, xml_index, param):
        return {
            command_type: f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:{action}({xml_index}, {param})')"
        }
        
    def _generate_get_command(self, command_type, grenton_id_part_0, grenton_id_part_1, action, xml_index):
        return {
            command_type: f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:{action}({xml_index})')"
        }
        
    async def async_turn_on(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            brightness = kwargs.get("brightness", self._last_brightness or 255)
            scaled_brightness = brightness / 255
            rgb_color = kwargs.get("rgb_color")
            command_brightness_mapping = {
                CONF_GRENTON_TYPE_DIMMER: {"action": "set", "index": 0, "param": scaled_brightness},
                CONF_GRENTON_TYPE_LED_R: {"action": "execute", "index": 3, "param": brightness},
                CONF_GRENTON_TYPE_LED_G: {"action": "execute", "index": 4, "param": brightness},
                CONF_GRENTON_TYPE_LED_B: {"action": "execute", "index": 5, "param": brightness},
                CONF_GRENTON_TYPE_LED_W: {"action": "execute", "index": 12, "param": brightness},
            }
            white = kwargs.get("white")

            # _LOGGER.info("[GrentonLight] turn_on | kwargs=%s", kwargs)
            
            if self._grenton_type in command_brightness_mapping:
                if grenton_id_part_1.startswith("ZWA"):
                    command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, "execute", 0, brightness)
                else:
                    config = command_brightness_mapping[self._grenton_type]
                    command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, config["action"], config["index"], config["param"])
                self._brightness = brightness
                self._last_brightness = brightness
            elif self._grenton_type == CONF_GRENTON_TYPE_RGB:
                if rgb_color:
                    hex_color = '#{:02x}{:02x}{:02x}'.format(*rgb_color)
                    hex_color = f'\\"{hex_color}\\"'
                    if grenton_id_part_1.startswith("ZWA"):
                        command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, "execute", 3, hex_color)
                    else:
                        command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, "execute", 6, hex_color)
                    self._rgb_color = rgb_color
                else:
                    command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, "execute", 0, scaled_brightness)
                    self._brightness = brightness
                    self._last_brightness = brightness
            elif self._grenton_type == CONF_GRENTON_TYPE_RGBW:
                if not white:
                    if rgb_color:
                        hex_color = '#{:02x}{:02x}{:02x}'.format(*rgb_color)
                        hex_color = f'\\"{hex_color}\\"'
                        if grenton_id_part_1.startswith("ZWA"):
                            command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, "execute", 3, hex_color)
                        else:
                            command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, "execute", 6, hex_color)
                        config = command_brightness_mapping[CONF_GRENTON_TYPE_LED_W]
                        command.update(self._generate_command("command_2", grenton_id_part_0, grenton_id_part_1, config["action"], config["index"], 0))
                        self._color_mode = ColorMode.RGB
                        self._rgb_color = rgb_color
                    else:
                        if self._color_mode == ColorMode.RGB:
                            command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, "execute", 0, scaled_brightness)
                            config = command_brightness_mapping[CONF_GRENTON_TYPE_LED_W]
                            command.update(self._generate_command("command_2", grenton_id_part_0, grenton_id_part_1, config["action"], config["index"], 0))
                        else:
                            config = command_brightness_mapping[CONF_GRENTON_TYPE_LED_W]
                            command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, config["action"], config["index"], brightness)
                            command.update(self._generate_command("command_2", grenton_id_part_0, grenton_id_part_1, "execute", 0, 0))
                        self._brightness = brightness
                        self._last_brightness = brightness
                else:
                    config = command_brightness_mapping[CONF_GRENTON_TYPE_LED_W]
                    command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, config["action"], config["index"], white)
                    command.update(self._generate_command("command_2", grenton_id_part_0, grenton_id_part_1, "execute", 0, 0))
                    self._color_mode = ColorMode.WHITE
                    self._white = white
                    self._brightness = white
                    self._last_brightness = white
            else:
                command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, "set", 0, 1)
            self._state = STATE_ON
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to turn on the light: %s", ex)
            
    async def async_turn_off(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command_mapping = {
                CONF_GRENTON_TYPE_RGB: {"action": "execute", "index": 0},
                CONF_GRENTON_TYPE_DIMMER: {"action": "set", "index": 0},
                CONF_GRENTON_TYPE_DOUT: {"action": "set", "index": 0},
                CONF_GRENTON_TYPE_LED_R: {"action": "execute", "index": 3},
                CONF_GRENTON_TYPE_LED_G: {"action": "execute", "index": 4},
                CONF_GRENTON_TYPE_LED_B: {"action": "execute", "index": 5},
                CONF_GRENTON_TYPE_LED_W: {"action": "execute", "index": 12},
            }
            
            if self._grenton_type == CONF_GRENTON_TYPE_DIMMER and grenton_id_part_1.startswith("ZWA"):
                config = {"action": "execute", "index": 0}
            else:
                config = command_mapping.get(self._grenton_type, {"action": "set", "index": 0})

            if self._grenton_type == CONF_GRENTON_TYPE_RGBW:
                if self._color_mode == ColorMode.WHITE:
                    config = command_mapping.get(CONF_GRENTON_TYPE_LED_W, {"action": "set", "index": 0})
                else:
                    config = command_mapping.get(CONF_GRENTON_TYPE_RGB, {"action": "set", "index": 0})
            
            command = self._generate_command("command", grenton_id_part_0, grenton_id_part_1, config["action"], config["index"], 0)
            self._last_brightness = self._brightness
            self._state = STATE_OFF
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to turn off the light: %s", ex)

    async def async_update(self):
        if not self._initialized:
            return
        
        if is_within_debounce(self._last_command_time, self.hass):
            return
            
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            xml_index__mapping = {
                CONF_GRENTON_TYPE_RGB: 0,
                CONF_GRENTON_TYPE_DOUT: 0,
                CONF_GRENTON_TYPE_DIMMER: 0,
                CONF_GRENTON_TYPE_LED_R: 3,
                CONF_GRENTON_TYPE_LED_G: 4,
                CONF_GRENTON_TYPE_LED_B: 5,
                CONF_GRENTON_TYPE_LED_W: 15,
            }
            
            if self._grenton_type in xml_index__mapping:
                command = self._generate_get_command("status", grenton_id_part_0, grenton_id_part_1, "get", xml_index__mapping[self._grenton_type])
            else:
                command = self._generate_get_command("status", grenton_id_part_0, grenton_id_part_1, "get", 0)
            
            if self._grenton_type == CONF_GRENTON_TYPE_RGB or self._grenton_type == CONF_GRENTON_TYPE_RGBW:
                if grenton_id_part_1.startswith("ZWA"):
                    command.update(self._generate_get_command("status_2", grenton_id_part_0, grenton_id_part_1, "get", 3))
                else:
                    command.update(self._generate_get_command("status_2", grenton_id_part_0, grenton_id_part_1, "get", 6))

            if self._grenton_type == CONF_GRENTON_TYPE_RGBW:
                command.update(self._generate_get_command("status_3", grenton_id_part_0, grenton_id_part_1, "get", 15))
            
            data = await self._api_client.get_status(command)

            if is_within_debounce(self._last_command_time, self.hass):
                return

            self._state = STATE_OFF if data.get("status") == 0 else STATE_ON
            if self._grenton_type == CONF_GRENTON_TYPE_RGB or self._grenton_type == CONF_GRENTON_TYPE_DIMMER:
                if self._grenton_type == CONF_GRENTON_TYPE_DIMMER and grenton_id_part_1.startswith("ZWA"):
                    self._brightness = data.get("status")
                    self._last_brightness = data.get("status")
                else:
                    self._brightness = data.get("status") * 255
                    self._last_brightness = data.get("status") * 255
            elif self._grenton_type == CONF_GRENTON_TYPE_LED_R or self._grenton_type == CONF_GRENTON_TYPE_LED_G or self._grenton_type == CONF_GRENTON_TYPE_LED_B or self._grenton_type == CONF_GRENTON_TYPE_LED_W:
                self._brightness = data.get("status")
                self._last_brightness = data.get("status")
            
            if self._grenton_type == CONF_GRENTON_TYPE_RGB:
                rgb_hex = data.get("status_2")
                if rgb_hex:
                    self._rgb_color = color_util.rgb_hex_to_rgb_list(rgb_hex.strip("#"))

            #rgbw
            if self._grenton_type == CONF_GRENTON_TYPE_RGBW:
                status_3 = data.get("status_3")
                if status_3 is not None and status_3 > 0:
                    self._state = STATE_ON
                    self._color_mode = ColorMode.WHITE
                    self._white = status_3
                    self._brightness = status_3
                    self._last_brightness = status_3
                elif data.get("status") is not None and data.get("status") > 0:
                    self._state = STATE_ON
                    self._color_mode = ColorMode.RGB
                    rgb_hex = data.get("status_2")
                    if rgb_hex:
                        self._rgb_color = color_util.rgb_hex_to_rgb_list(rgb_hex.strip("#"))
                    self._brightness = data.get("status") * 255
                    self._last_brightness = data.get("status") * 255
                else:
                    self._state = STATE_OFF

            self.async_write_ha_state()

        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to update the light state: %s", ex)
            self._state = None
        except (AttributeError, TypeError, ValueError) as ex:
            _LOGGER.error("Unexpected data in light state response: %s", ex)
            self._state = None
