"""
==================================================
Author: Jan Nalepka
Script version: 3.5
Date: 15.11.2025
Repository: https://github.com/jnalepka/grenton-objects-home-assistant
==================================================
"""

import voluptuous as vol
from homeassistant import config_entries
from .const import (
    CONF_API_ENDPOINT,
    CONF_AUTO_UPDATE,
    CONF_UPDATE_INTERVAL, 
    DEFAULT_UPDATE_INTERVAL,
    CONF_REVERSED,
    CONF_GRENTON_TYPE,
    LIGHT_GRENTON_TYPE_OPTIONS,
    SENSOR_GRENTON_TYPE_OPTIONS,
    SWITCH_GRENTON_TYPE_OPTIONS,
    CONF_DEVICE_CLASS
)
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig


class GrentonOptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        device_type = self.config_entry.data.get("device_type", "")

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        default_endpoint = self.config_entry.options.get(
            CONF_API_ENDPOINT,
            self.config_entry.data.get(CONF_API_ENDPOINT)
        )

        default_auto_update = self.config_entry.options.get(
            CONF_AUTO_UPDATE, 
            self.config_entry.data.get(CONF_AUTO_UPDATE, True)
        )

        default_update_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

        data_schema = vol.Schema({
            vol.Required(CONF_API_ENDPOINT, default=default_endpoint): str
        })

        if device_type == "light":
            default_type = self.config_entry.options.get(CONF_GRENTON_TYPE, self.config_entry.data.get(CONF_GRENTON_TYPE))
            data_schema = data_schema.extend({
                vol.Required(CONF_GRENTON_TYPE, default=default_type): vol.In(LIGHT_GRENTON_TYPE_OPTIONS)
            })
        elif device_type == "cover":
            default_reversed = self.config_entry.options.get(CONF_REVERSED, self.config_entry.data.get(CONF_REVERSED))
            default_device_type = self.config_entry.options.get(CONF_DEVICE_CLASS, self.config_entry.data.get(CONF_DEVICE_CLASS, CoverDeviceClass.BLIND.value))
            data_schema = data_schema.extend({
                vol.Required(CONF_DEVICE_CLASS, default=default_device_type): SelectSelector(
                    SelectSelectorConfig(
                        options=[dc.value for dc in CoverDeviceClass],
                        translation_key="device_class"
                    )
                ),
                vol.Required(CONF_REVERSED, default=default_reversed): bool
            })
        elif device_type == "sensor":
            default_type = self.config_entry.options.get(CONF_GRENTON_TYPE, self.config_entry.data.get(CONF_GRENTON_TYPE))
            data_schema = data_schema.extend({
                vol.Required(CONF_GRENTON_TYPE, default=default_type): vol.In(SENSOR_GRENTON_TYPE_OPTIONS)
            })
        elif device_type == "switch":
            default_type = self.config_entry.options.get(CONF_GRENTON_TYPE, self.config_entry.data.get(CONF_GRENTON_TYPE, 'DOUT'))
            data_schema = data_schema.extend({
                vol.Required(CONF_GRENTON_TYPE, default=default_type): vol.In(SWITCH_GRENTON_TYPE_OPTIONS)
            })

        if device_type == "climate":
            data_schema = data_schema.extend({
                vol.Required(CONF_UPDATE_INTERVAL, default=default_update_interval): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600))
            })
        elif device_type != "button":
            data_schema = data_schema.extend({
                vol.Required(CONF_AUTO_UPDATE, default=default_auto_update): bool,
                vol.Required(CONF_UPDATE_INTERVAL, default=default_update_interval): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600))
            })

        return self.async_show_form(
            step_id="init", 
            data_schema=data_schema, 
            description_placeholders={
                "grenton_id": self.config_entry.data.get("grenton_id")
            }
        )