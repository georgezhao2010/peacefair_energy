import logging
from homeassistant.core import callback
from homeassistant import config_entries
import voluptuous as vol

from .const import (
    DOMAIN,
    DEFAULT_SLAVE,
    DEFAULT_PROTOCOL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEVICES,
    PROTOCOLS
)

from homeassistant.const import (
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None, error=None):

        if user_input is not None:
            if DOMAIN in self.hass.data and DEVICES in self.hass.data[DOMAIN] and \
                    user_input[CONF_HOST] in self.hass.data[DOMAIN][DEVICES]:
                return await self.async_step_user(error="device_exist")
            else:
                return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): vol.In(PROTOCOLS.keys()),
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE): vol.Coerce(int)
            }),
            errors={"base": error} if error else None
        )
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=scan_interval,
                ): vol.All(vol.Coerce(int)),
            }),
        )
