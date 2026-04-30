"""
==================================================
Author: Jan Nalepka
Script version: 3.2
Date: 30.04.2026
Repository: https://github.com/jnalepka/grenton-objects-home-assistant
==================================================
"""

import aiohttp
from .const import (
    CONF_API_ENDPOINT,
    CONF_GRENTON_ID,
    CONF_OBJECT_NAME,
    CONF_GRENTON_TYPE,
    CONF_AUTO_UPDATE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN
)
import logging
import voluptuous as vol
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    PLATFORM_SCHEMA
)
from homeassistant.const import (STATE_ON, STATE_OFF)
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

CONF_GRENTON_TYPE_BINARY_SENSOR_DIN = "BINARY_SENSOR_DIN"
CONF_GRENTON_TYPE_BINARY_SENSOR_SATEL = "BINARY_SENSOR_SATEL"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_ENDPOINT): str,
    vol.Required(CONF_GRENTON_ID): str,
    vol.Required(CONF_GRENTON_TYPE, default=CONF_GRENTON_TYPE_BINARY_SENSOR_DIN): vol.In([
        CONF_GRENTON_TYPE_BINARY_SENSOR_DIN,
        CONF_GRENTON_TYPE_BINARY_SENSOR_SATEL
    ]),
    vol.Optional(CONF_OBJECT_NAME, default='Grenton Binary Sensor'): str
})

async def async_setup_entry(hass, config_entry, async_add_entities):
    api_endpoint = config_entry.options.get(CONF_API_ENDPOINT, config_entry.data.get(CONF_API_ENDPOINT))
    grenton_id = config_entry.data.get(CONF_GRENTON_ID)
    grenton_type = config_entry.options.get(CONF_GRENTON_TYPE, config_entry.data.get(CONF_GRENTON_TYPE, CONF_GRENTON_TYPE_BINARY_SENSOR_DIN))
    object_name = config_entry.data.get(CONF_OBJECT_NAME)
    auto_update = config_entry.options.get(CONF_AUTO_UPDATE, config_entry.data.get(CONF_AUTO_UPDATE, True))
    update_interval = config_entry.options.get(CONF_UPDATE_INTERVAL, config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))

    entity = GrentonBinarySensor(api_endpoint, grenton_id, grenton_type, object_name, auto_update, update_interval)
    async_add_entities([entity], True)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entities": {}}

    hass.data[DOMAIN]["entities"][entity.entity_id] = entity

class GrentonBinarySensor(BinarySensorEntity):
    def __init__(self, api_endpoint, grenton_id, grenton_type, object_name, auto_update, update_interval):
        self._api_endpoint = api_endpoint
        self._grenton_id = grenton_id
        self._grenton_type = grenton_type
        self._object_name = object_name
        self._unique_id = f"grenton_{grenton_id.split('->')[1]}"
        self._state = None
        self._auto_update = auto_update
        self._update_interval = update_interval
        self._unsub_interval = None
        self._initialized = False

    async def async_added_to_hass(self):
        self._initialized = True
        if self._auto_update:
            self._unsub_interval = async_track_time_interval(
                self.hass, self._update_callback, timedelta(seconds=self._update_interval)
            )
            await self.async_update()

    async def async_will_remove_from_hass(self):
        if self._unsub_interval:
            self._unsub_interval()

    async def _update_callback(self, now):
        await self.async_update()

    async def async_force_state(self, state: int):
        self._state = STATE_ON if state == 1 else STATE_OFF
        self.async_write_ha_state()

    @property
    def name(self):
        return self._object_name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        return self._state == STATE_ON

    @property
    def device_class(self):
        return "door"

    @property
    def should_poll(self):
        return False

    async def async_update(self):
        if not self._initialized:
            return

        try:
            grenton_id_part_0, grenton_id_part_1 = self._grenton_id.split('->')

            if self._grenton_type == CONF_GRENTON_TYPE_BINARY_SENSOR_SATEL:
                command = {"command": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(0)')"}
            else:
                command = {"status": f"return {grenton_id_part_0}:execute(0, '{grenton_id_part_1}:get(0)')"}

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._api_endpoint}", json=command) as response:
                    response.raise_for_status()
                    data = await response.json()

                    if self._grenton_type == CONF_GRENTON_TYPE_BINARY_SENSOR_SATEL:
                        self._state = STATE_OFF if data.get("command") == 0 else STATE_ON
                    else:
                        self._state = STATE_OFF if data.get("status") == 0 else STATE_ON

                    self.async_write_ha_state()
        except aiohttp.ClientError as ex:
            _LOGGER.error(f"Failed to update the binary sensor state: {ex}")
            self._state = None