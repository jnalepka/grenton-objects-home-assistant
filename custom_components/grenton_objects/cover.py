"""
==================================================
Author: Jan Nalepka
Script version: 3.6
Date: 23.12.2025
Repository: https://github.com/jnalepka/grenton-objects-home-assistant
==================================================
"""

import aiohttp
from .const import (
    CONF_API_ENDPOINT,
    CONF_GRENTON_ID,
    CONF_OBJECT_NAME,
    CONF_REVERSED,
    CONF_AUTO_UPDATE,
    CONF_UPDATE_INTERVAL, 
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    CONF_DEVICE_CLASS
)
from .api import get_api_client, GrentonApiError
from .mixins import GrentonPollingMixin, is_within_debounce
import logging
import voluptuous as vol
from homeassistant.components.cover import (
    CoverEntity,
    PLATFORM_SCHEMA,
    CoverDeviceClass,
    CoverEntityFeature
)
from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_ENDPOINT): str,
    vol.Required(CONF_GRENTON_ID): str,
    vol.Required(CONF_REVERSED, default=False): bool,
    vol.Optional(CONF_OBJECT_NAME, default='Grenton Cover'): str,
    vol.Optional(CONF_DEVICE_CLASS, default=''): str,
})

async def async_setup_entry(hass, config_entry, async_add_entities):
    api_endpoint = config_entry.options.get(CONF_API_ENDPOINT, config_entry.data.get(CONF_API_ENDPOINT))
    grenton_id = config_entry.data.get(CONF_GRENTON_ID)
    reversed = config_entry.options.get(CONF_REVERSED, config_entry.data.get(CONF_REVERSED))
    object_name = config_entry.data.get(CONF_OBJECT_NAME)
    auto_update = config_entry.options.get(CONF_AUTO_UPDATE, config_entry.data.get(CONF_AUTO_UPDATE, True))
    update_interval = config_entry.options.get(CONF_UPDATE_INTERVAL, config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    device_class = config_entry.options.get(CONF_DEVICE_CLASS, config_entry.data.get(CONF_DEVICE_CLASS, CoverDeviceClass.BLIND.value))

    api_client = get_api_client(hass, api_endpoint)
    entity = GrentonCover(api_endpoint, grenton_id, reversed, object_name, auto_update, update_interval, device_class, api_client)
    async_add_entities([entity], True)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entities": {}}

    hass.data[DOMAIN]["entities"][entity.entity_id] = entity

class GrentonCover(GrentonPollingMixin, CoverEntity):
    def __init__(self, api_endpoint, grenton_id, reversed, object_name, auto_update, update_interval, device_class, api_client):
        self._device_class = device_class
        self._api_endpoint = api_endpoint
        self._grenton_id = grenton_id
        self._reversed = reversed
        self._object_name = object_name
        self._state = None
        self._current_cover_position = 0
        self._current_cover_tilt_position = 0
        self._unique_id = f"grenton_{grenton_id.split('->')[1]}"
        self._last_command_time = None
        self._auto_update = auto_update
        self._update_interval = update_interval
        self._unsub_interval = None
        self._initialized = False
        self._api_client = api_client

    async def async_force_cover(self, state: int, position: int, lamel: int):
        if self._reversed:
            position = 100 - position
        self._state = STATE_CLOSED if position == 0 else STATE_OPEN
        if state == 1:
            self._state = STATE_OPENING
        elif state == 2:
            self._state = STATE_CLOSING
        self._current_cover_position = position
        if lamel is not None:
            self._current_cover_tilt_position = int((90 - lamel) * 100 / 90)
        self.async_write_ha_state()

    @property
    def name(self):
        return self._object_name

    @property
    def is_closed(self):
        return self._state == STATE_CLOSED

    @property
    def is_opening(self):
        return self._state == STATE_OPENING

    @property
    def is_closing(self):
        return self._state == STATE_CLOSING

    @property
    def current_cover_position(self):
        return self._current_cover_position
    
    @property
    def current_cover_tilt_position(self):
        return self._current_cover_tilt_position

    @property
    def unique_id(self):
        return self._unique_id
    
    @property
    def should_poll(self):
        return False
    
    @property
    def device_class(self):
        return self._device_class
    
    @property
    def supported_features(self):
        base_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )

        if self._device_class == CoverDeviceClass.BLIND.value:
            base_features |= (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.STOP_TILT
                | CoverEntityFeature.SET_TILT_POSITION
            )

        return base_features

    async def async_open_cover(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(0, 0)')"}
            self._state = STATE_OPENING
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to open the cover: %s", ex)

    async def async_close_cover(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(1, 0)')"}
            self._state = STATE_CLOSING
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to close the cover: %s", ex)

    async def async_stop_cover(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(3, 0)')"}
            self._state = STATE_OPEN
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to stop the cover: %s", ex)

    async def async_set_cover_position(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            position = kwargs.get("position", 100)
            prev_position = self._current_cover_position
            self._current_cover_position = position
            if self._reversed:
                position = 100 - position
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(10, {position})')"}
            if grenton_id_part_1.startswith("ZWA"):
                command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(7, {position})')"}
            if (position > prev_position):
                if self._reversed:
                    self._state = STATE_CLOSING
                else:
                    self._state = STATE_OPENING
            else:
                if self._reversed:
                    self._state = STATE_OPENING
                else:
                    self._state = STATE_CLOSING
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to set the cover position: %s", ex)

    async def async_set_cover_tilt_position(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            tilt_position = kwargs.get("tilt_position", 100)
            self._current_cover_tilt_position = tilt_position
            tilt_position = int((100 - tilt_position) * 90 / 100)
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(9, {tilt_position})')"}
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to set the cover tilt position: %s", ex)

    async def async_open_cover_tilt(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(9, 0)')"}
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to open the cover tilt: %s", ex)

    async def async_close_cover_tilt(self, **kwargs):
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            command = {"command": f"{grenton_id_part_0}:execute(0, '{grenton_id_part_1}:execute(9, 90)')"}
            self._last_command_time = self.hass.loop.time() if self.hass is not None else None
            self.async_write_ha_state()
            
            await self._api_client.send_command(command)
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to close the cover tilt: %s", ex)

    async def async_update(self):
        if not self._initialized:
            return
        
        if is_within_debounce(self._last_command_time, self.hass):
            return
            
        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')
            if grenton_id_part_1.startswith("ZWA"):
                command = {"status": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(2)')"}
            else:
                command = {"status": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(0)')"}
            if grenton_id_part_1.startswith("ZWA"):
                command.update({"status_2": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(4)')"})
            else:
                command.update({"status_2": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(7)')"})
            if grenton_id_part_1.startswith("ZWA"):
                command.update({"status_3": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(6)')"})
            else:
                command.update({"status_3": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(8)')"})
            data = await self._api_client.get_status(command)

            if is_within_debounce(self._last_command_time, self.hass):
                return

            position = data.get("status_2")
            if position is None:
                _LOGGER.warning("Cover position unavailable (status_2 missing)")
                return
            if self._reversed:
                position = 100 - position
            self._state = STATE_CLOSED if position == 0 else STATE_OPEN
            if data.get("status") == 1:
                self._state = STATE_OPENING
            elif data.get("status") == 2:
                self._state = STATE_CLOSING
            self._current_cover_position = position
            angle = data.get("status_3", 0)
            self._current_cover_tilt_position = int((90 - angle) * 100 / 90)
            self.async_write_ha_state()
        except (aiohttp.ClientError, GrentonApiError) as ex:
            _LOGGER.error("Failed to update the cover state: %s", ex)
            self._state = None
