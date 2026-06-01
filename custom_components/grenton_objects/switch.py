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
    CONF_AUTO_UPDATE,
    CONF_UPDATE_INTERVAL, 
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN
)
from .api import get_api_client, GrentonApiError
from .mixins import GrentonPollingMixin, is_within_debounce

import logging
import voluptuous as vol
from homeassistant.components.switch import (
    SwitchEntity,
    PLATFORM_SCHEMA
)
from homeassistant.const import (STATE_ON, STATE_OFF)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_ENDPOINT): str,
    vol.Required(CONF_GRENTON_ID): str,
    vol.Optional(CONF_OBJECT_NAME, default='Grenton Switch'): str
})

async def async_setup_entry(hass, config_entry, async_add_entities):
    api_endpoint = config_entry.options.get(CONF_API_ENDPOINT, config_entry.data.get(CONF_API_ENDPOINT))
    grenton_id = config_entry.data.get(CONF_GRENTON_ID)
    object_name = config_entry.data.get(CONF_OBJECT_NAME)
    auto_update = config_entry.options.get(CONF_AUTO_UPDATE, config_entry.data.get(CONF_AUTO_UPDATE, True))
    update_interval = config_entry.options.get(CONF_UPDATE_INTERVAL, config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))

    api_client = get_api_client(hass, api_endpoint)
    entity = GrentonSwitch(api_endpoint, grenton_id, object_name, auto_update, update_interval, api_client)
    async_add_entities([entity], True)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entities": {}}

    hass.data[DOMAIN]["entities"][entity.entity_id] = entity

class GrentonSwitch(GrentonPollingMixin, SwitchEntity):
    def __init__(self, api_endpoint, grenton_id, object_name, auto_update, update_interval, api_client):
        self._api_endpoint = api_endpoint
        self._grenton_id = grenton_id
        self._object_name = object_name
        self._state = None
        self._unique_id = f"grenton_{grenton_id.split('->')[1]}"
        self._last_command_time = None
        self._auto_update = auto_update
        self._update_interval = update_interval
        self._unsub_interval = None
        self._initialized = False
        self._api_client = api_client

    async def async_force_state(self, state: int):
        self._state = STATE_ON if state == 1 else STATE_OFF
        self.async_write_ha_state()

    @property
    def name(self):
        return self._object_name

    @property
    def is_on(self):
        return self._state == STATE_ON

    @property
    def unique_id(self):
        return self._unique_id
    
    @property
    def should_poll(self):
        return False

    async def async_turn_on(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:set(0, 1)')"}
            self._state = STATE_ON
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to turn on the switch: %s", ex)

    async def async_turn_off(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:set(0, 0)')"}
            self._state = STATE_OFF
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to turn off the switch: %s", ex)

    async def async_update(self):
        if not self._initialized:
            return
        
        if is_within_debounce(self._last_command_time, self.hass):
            return
            
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command = {"status": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(0)')"}
            data = await self._api_client.get_status(command)

            if is_within_debounce(self._last_command_time, self.hass):
                return

            self._state = STATE_OFF if data.get("status") == 0 else STATE_ON
            self.async_write_ha_state()
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to update the switch state: %s", ex)
            self._state = None
