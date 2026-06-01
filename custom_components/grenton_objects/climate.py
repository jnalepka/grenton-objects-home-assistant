"""
==================================================
Author: Jan Nalepka
Script version: 3.3
Date: 20.10.2025
Repository: https://github.com/jnalepka/grenton-objects-home-assistant
==================================================
"""

import aiohttp
from .const import (
    CONF_API_ENDPOINT,
    CONF_GRENTON_ID,
    CONF_OBJECT_NAME,
    CONF_UPDATE_INTERVAL, 
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN
)
from .api import get_api_client, GrentonApiError
from .mixins import GrentonPollingMixin, is_within_debounce
import logging
import voluptuous as vol
from homeassistant.components.climate import (
    ClimateEntity,
    PLATFORM_SCHEMA,
    HVACMode,
    ClimateEntityFeature
)
from homeassistant.const import UnitOfTemperature

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_ENDPOINT): str,
    vol.Required(CONF_GRENTON_ID): str,
    vol.Optional(CONF_OBJECT_NAME, default='Grenton Thermostat'): str
})

async def async_setup_entry(hass, config_entry, async_add_entities):
    api_endpoint = config_entry.options.get(CONF_API_ENDPOINT, config_entry.data.get(CONF_API_ENDPOINT))
    grenton_id = config_entry.data.get(CONF_GRENTON_ID)
    object_name = config_entry.data.get(CONF_OBJECT_NAME)
    auto_update = True
    update_interval = config_entry.options.get(CONF_UPDATE_INTERVAL, config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))

    api_client = get_api_client(hass, api_endpoint)
    entity = GrentonClimate(api_endpoint, grenton_id, object_name, auto_update, update_interval, api_client)
    async_add_entities([entity], True)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entities": {}}

    hass.data[DOMAIN]["entities"][entity.entity_id] = entity

class GrentonClimate(GrentonPollingMixin, ClimateEntity):
    _enable_turn_on_off_backwards_compatibility = False
    
    def __init__(self, api_endpoint, grenton_id, object_name, auto_update, update_interval, api_client):
        self._api_endpoint = api_endpoint
        self._grenton_id = grenton_id
        self._name = object_name
        self._current_temperature = None
        self._target_temperature = None
        self._hvac_mode = HVACMode.OFF
        self._hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
        self._unique_id = f"grenton_{grenton_id.split('->')[1]}"
        self._temperature_unit = UnitOfTemperature.CELSIUS
        self._supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._last_command_time = None
        self._auto_update = auto_update
        self._update_interval = update_interval
        self._unsub_interval = None
        self._initialized = False
        self._api_client = api_client

    async def async_force_therm_state(self, state: int, direction: int):
        self._hvac_mode = HVACMode.OFF if state == 0 else (HVACMode.COOL if direction == 1 else HVACMode.HEAT)
        self.async_write_ha_state()

    async def async_force_therm_target_temp(self, temp: float):
        self._target_temperature = temp
        self.async_write_ha_state()

    async def async_force_therm_current_temp(self, temp: float):
        self._current_temperature = temp
        self.async_write_ha_state()

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return self._temperature_unit

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return self._hvac_modes

    @property
    def unique_id(self):
        return self._unique_id
    
    @property
    def supported_features(self):
        return self._supported_features
    
    @property
    def should_poll(self):
        return False


    async def async_set_temperature(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            temperature = kwargs.get("temperature", 20)
            self._target_temperature = temperature
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:set(8, 0)')"}
            command.update({"command_2": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:set(3, {temperature})')"})
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to set the climate temperature: %s", ex)

    async def async_set_hvac_mode(self, hvac_mode):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            self._hvac_mode = hvac_mode
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(1, 0)')"}
            if hvac_mode == HVACMode.HEAT:
                command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(0, 0)')"}
                command.update({"command_2": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:set(7, 0)')"})
            elif hvac_mode == HVACMode.COOL:
                command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(0, 0)')"}
                command.update({"command_2": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:set(7, 1)')"})
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to set the climate hvac_mode: %s", ex)
        

    async def async_update(self):
        if not self._initialized:
            return
        
        if is_within_debounce(self._last_command_time, self.hass):
            return
        
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command = {"status": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(6)')"}
            command.update({"status_2": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(7)')"})
            command.update({"status_3": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(12)')"})
            command.update({"status_4": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(14)')"})
            data = await self._api_client.get_status(command)

            if is_within_debounce(self._last_command_time, self.hass):
                return

            self._hvac_mode = HVACMode.OFF if data.get("status") == 0 else (HVACMode.COOL if data.get("status_2") == 1 else HVACMode.HEAT)
            self._target_temperature = data.get("status_3")
            self._current_temperature = data.get("status_4")
            self.async_write_ha_state()
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to update the climate state: %s", ex)
