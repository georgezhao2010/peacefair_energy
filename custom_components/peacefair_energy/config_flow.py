"""Peacefair Energy Monitor 集成的 Config Flow。"""
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DEFAULT_PORT,
    DEFAULT_PROTOCOL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
    PROTOCOLS,
    CONF_SUMMER_MONTHS,
    CONF_SUMMER_TIER1,
    CONF_SUMMER_TIER2,
    CONF_NON_SUMMER_TIER1,
    CONF_NON_SUMMER_TIER2,
    CONF_SUMMER_PRICE_L1,
    CONF_SUMMER_PRICE_L2,
    CONF_SUMMER_PRICE_L3,
    CONF_NON_SUMMER_PRICE_L1,
    CONF_NON_SUMMER_PRICE_L2,
    CONF_NON_SUMMER_PRICE_L3,
    # 舊的鍵用於遷移
    CONF_PRICE_L1,
    CONF_PRICE_L2,
    CONF_PRICE_L3,
    # 默認值
    DEFAULT_SUMMER_MONTHS,
    DEFAULT_SUMMER_TIER1,
    DEFAULT_SUMMER_TIER2,
    DEFAULT_NON_SUMMER_TIER1,
    DEFAULT_NON_SUMMER_TIER2,
    DEFAULT_SUMMER_PRICE_L1,
    DEFAULT_SUMMER_PRICE_L2,
    DEFAULT_SUMMER_PRICE_L3,
    DEFAULT_NON_SUMMER_PRICE_L1,
    DEFAULT_NON_SUMMER_PRICE_L2,
    DEFAULT_NON_SUMMER_PRICE_L3,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
)

_LOGGER = logging.getLogger(__name__)


class PeacefairConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """處理 Peacefair Energy Monitor 的配置流程。"""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """處理初始步驟。"""
        errors = {}

        if user_input is not None:
            unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_HOST], data=user_input
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): vol.In(
                    list(PROTOCOLS.keys())
                ),
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE): vol.Coerce(int),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """獲取選項流程處理器。"""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """處理 Peacefair 集成的選項。"""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """初始化選項流程。"""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """管理選項。"""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._config_entry.options
        scan_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        
        summer_months = options.get(CONF_SUMMER_MONTHS, DEFAULT_SUMMER_MONTHS)
        summer_t1 = options.get(CONF_SUMMER_TIER1, DEFAULT_SUMMER_TIER1)
        summer_t2 = options.get(CONF_SUMMER_TIER2, DEFAULT_SUMMER_TIER2)
        non_summer_t1 = options.get(CONF_NON_SUMMER_TIER1, DEFAULT_NON_SUMMER_TIER1)
        non_summer_t2 = options.get(CONF_NON_SUMMER_TIER2, DEFAULT_NON_SUMMER_TIER2)
        
        # 智能遷移：如果沒有新的價格設置，嘗試使用舊的設置，否則使用默認值
        old_p1 = options.get(CONF_PRICE_L1, DEFAULT_SUMMER_PRICE_L1)
        old_p2 = options.get(CONF_PRICE_L2, DEFAULT_SUMMER_PRICE_L2)
        old_p3 = options.get(CONF_PRICE_L3, DEFAULT_SUMMER_PRICE_L3)

        summer_p1 = options.get(CONF_SUMMER_PRICE_L1, old_p1)
        summer_p2 = options.get(CONF_SUMMER_PRICE_L2, old_p2)
        summer_p3 = options.get(CONF_SUMMER_PRICE_L3, old_p3)

        non_summer_p1 = options.get(CONF_NON_SUMMER_PRICE_L1, old_p1)
        non_summer_p2 = options.get(CONF_NON_SUMMER_PRICE_L2, old_p2)
        non_summer_p3 = options.get(CONF_NON_SUMMER_PRICE_L3, old_p3)

        options_schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): cv.positive_int,
                vol.Optional(CONF_SUMMER_MONTHS, default=summer_months): str,
                vol.Optional(CONF_SUMMER_TIER1, default=summer_t1): int,
                vol.Optional(CONF_SUMMER_TIER2, default=summer_t2): int,
                vol.Optional(CONF_NON_SUMMER_TIER1, default=non_summer_t1): int,
                vol.Optional(CONF_NON_SUMMER_TIER2, default=non_summer_t2): int,
                
                # 夏季價格
                vol.Optional(CONF_SUMMER_PRICE_L1, default=summer_p1): float,
                vol.Optional(CONF_SUMMER_PRICE_L2, default=summer_p2): float,
                vol.Optional(CONF_SUMMER_PRICE_L3, default=summer_p3): float,

                # 非夏季價格
                vol.Optional(CONF_NON_SUMMER_PRICE_L1, default=non_summer_p1): float,
                vol.Optional(CONF_NON_SUMMER_PRICE_L2, default=non_summer_p2): float,
                vol.Optional(CONF_NON_SUMMER_PRICE_L3, default=non_summer_p3): float,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)