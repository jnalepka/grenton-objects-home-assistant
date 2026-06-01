"""
==================================================
Author: Jan Nalepka
Script version: 3.3
Date: 29.12.2025
Repository: https://github.com/jnalepka/grenton-objects-home-assistant
==================================================
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN, CONF_API_ENDPOINT
from homeassistant.exceptions import ServiceValidationError
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_SET_STATE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): str,
    vol.Required("state"): vol.In([0, 1])
})

SERVICE_SET_BRIGHTNESS_SCHEMA = vol.Schema({
    vol.Required("entity_id"): str,
    vol.Required("brightness"): vol.All(
        vol.Coerce(float),
        vol.Range(min=0.0, max=255.0)
    )
})

SERVICE_SET_RGB_SCHEMA = vol.Schema({
    vol.Required("entity_id"): str,
    vol.Required("hex"): vol.Match(r"^#[0-9A-Fa-f]{6}$")
})

SERVICE_SET_RGBW_SCHEMA = vol.Schema({
    vol.Required("entity_id"): str,
    vol.Required("hex"): vol.Match(r"^#[0-9A-Fa-f]{6}$"),
    vol.Required("brightness"): vol.All(
        vol.Coerce(float),
        vol.Range(min=0.0, max=255.0)
    ),
    vol.Required("white"): vol.All(
        vol.Coerce(float),
        vol.Range(min=0.0, max=255.0)
    )
})

SERVICE_SET_VALUE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): str,
    vol.Required("value"): vol.All(
        vol.Coerce(float),
        vol.Range(min=-999999999, max=999999999)
    )
})

SERVICE_SET_COVER_SCHEMA = vol.Schema({
    vol.Required("entity_id"): str,
    vol.Required("state"): vol.In([0, 1, 2, 3, 4]),
    vol.Required("position"): vol.All(
        vol.Coerce(int),
        vol.Range(min=0, max=100)
    ),
    vol.Optional("lamel"): vol.All(
        vol.Coerce(int),
        vol.Range(min=0, max=90)
    )
})

SERVICE_SET_THERM_STATE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): str,
    vol.Required("state"): vol.In([0, 1]),
    vol.Optional("direction"): vol.In([0, 1])
})

SERVICE_SET_THERM_TEMP_SCHEMA = vol.Schema({
    vol.Required("entity_id"): str,
    vol.Required("temp"): vol.All(
        vol.Coerce(float),
        vol.Range(min=-999999999, max=999999999)
    )
})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def handle_set_state(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        state = call.data["state"]
        entity = hass.data.get(DOMAIN, {}).get("entities", {}).get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Encja {entity_id} nie została znaleziona")
        try:
            await entity.async_force_state(state)
        except Exception as err:
            raise ServiceValidationError(
                f"Nie udało się ustawić stanu dla encji {entity_id}: {err}"
            ) from err
        
    async def handle_set_brightness(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        brightness = call.data["brightness"]
        entity = hass.data.get(DOMAIN, {}).get("entities", {}).get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Encja {entity_id} nie została znaleziona")
        try:
            await entity.async_force_brightness(brightness)
        except Exception as err:
            raise ServiceValidationError(
                f"Nie udało się ustawić jasności dla encji {entity_id}: {err}"
            ) from err
        
    async def handle_set_rgb(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        hex = call.data["hex"]
        entity = hass.data.get(DOMAIN, {}).get("entities", {}).get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Encja {entity_id} nie została znaleziona")
        try:
            await entity.async_force_rgb(hex)
        except Exception as err:
            raise ServiceValidationError(
                f"Nie udało się ustawić rgb hex dla encji {entity_id}: {err}"
            ) from err

    async def handle_set_rgbw(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        hex = call.data["hex"]
        brightness = call.data["brightness"]
        white = call.data["white"]
        entity = hass.data.get(DOMAIN, {}).get("entities", {}).get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Encja {entity_id} nie została znaleziona")
        try:
            await entity.async_force_rgbw(hex, brightness, white)
        except Exception as err:
            raise ServiceValidationError(
                f"Nie udało się ustawić rgbw dla encji {entity_id}: {err}"
            ) from err
        
    async def handle_set_value(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        value = call.data["value"]
        entity = hass.data.get(DOMAIN, {}).get("entities", {}).get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Encja {entity_id} nie została znaleziona")
        try:
            await entity.async_force_value(value)
        except Exception as err:
            raise ServiceValidationError(
                f"Nie udało się ustawić wartości dla encji {entity_id}: {err}"
            ) from err
        
    async def handle_set_cover(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        state = call.data["state"]
        position = call.data["position"]
        lamel  = call.data.get("lamel")
        entity = hass.data.get(DOMAIN, {}).get("entities", {}).get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Encja {entity_id} nie została znaleziona")
        try:
            await entity.async_force_cover(state, position, lamel)
        except Exception as err:
            raise ServiceValidationError(
                f"Nie udało się ustawić roller shuttera dla encji {entity_id}: {err}"
            ) from err
        
    async def handle_set_therm_state(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        state = call.data["state"]
        direction = call.data.get("direction", 0)
        entity = hass.data.get(DOMAIN, {}).get("entities", {}).get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Encja {entity_id} nie została znaleziona")
        try:
            await entity.async_force_therm_state(state, direction)
        except Exception as err:
            raise ServiceValidationError(
                f"Nie udało się ustawić stanu termostatu dla encji {entity_id}: {err}"
            ) from err
        
    async def handle_set_therm_target_temp(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        temp = call.data["temp"]
        entity = hass.data.get(DOMAIN, {}).get("entities", {}).get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Encja {entity_id} nie została znaleziona")
        try:
            await entity.async_force_therm_target_temp(temp)
        except Exception as err:
            raise ServiceValidationError(
                f"Nie udało się ustawić docelowej temperatury termostatu dla encji {entity_id}: {err}"
            ) from err
    
    async def handle_set_therm_current_temp(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        temp = call.data["temp"]
        entity = hass.data.get(DOMAIN, {}).get("entities", {}).get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Encja {entity_id} nie została znaleziona")
        try:
            await entity.async_force_therm_current_temp(temp)
        except Exception as err:
            raise ServiceValidationError(
                f"Nie udało się ustawić aktualnej temperatury termostatu dla encji {entity_id}: {err}"
            ) from err

    services = [
    ("set_state", handle_set_state, SERVICE_SET_STATE_SCHEMA),
    ("set_brightness", handle_set_brightness, SERVICE_SET_BRIGHTNESS_SCHEMA),
    ("set_rgb", handle_set_rgb, SERVICE_SET_RGB_SCHEMA),
    ("set_rgbw", handle_set_rgbw, SERVICE_SET_RGBW_SCHEMA),
    ("set_value", handle_set_value, SERVICE_SET_VALUE_SCHEMA),
    ("set_cover", handle_set_cover, SERVICE_SET_COVER_SCHEMA),
    ("set_therm_state", handle_set_therm_state, SERVICE_SET_THERM_STATE_SCHEMA),
    ("set_therm_target_temp", handle_set_therm_target_temp, SERVICE_SET_THERM_TEMP_SCHEMA),
    ("set_therm_current_temp", handle_set_therm_current_temp, SERVICE_SET_THERM_TEMP_SCHEMA),
]

    for name, handler, schema in services:
        hass.services.async_register(DOMAIN, name, handler, schema=schema)
        
    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    config_entry.async_on_unload(
        config_entry.add_update_listener(async_update_options)
    )

    device = config_entry.data
    platform = device["device_type"]
    if platform:
        await hass.config_entries.async_forward_entry_setups(config_entry, {platform})
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    device_type = config_entry.data.get("device_type")
    if device_type:
        unload_ok = await hass.config_entries.async_unload_platforms(config_entry, [device_type])
        # Remove cached API client if endpoint is no longer referenced
        if unload_ok:
            api_endpoint = config_entry.data.get(CONF_API_ENDPOINT)
            if api_endpoint:
                remaining = hass.config_entries.async_entries(DOMAIN)
                still_used = any(
                    entry.entry_id != config_entry.entry_id
                    and entry.data.get(CONF_API_ENDPOINT) == api_endpoint
                    for entry in remaining
                )
                if not still_used:
                    clients = hass.data.get(DOMAIN, {}).get("clients", {})
                    client = clients.pop(api_endpoint, None)
                    if client:
                        client.close()
        return unload_ok
    return False
