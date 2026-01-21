"""
Peacefair Energy Monitor 自定義組件。

用於與 Peacefair 能源監測器通訊的 Home Assistant 自定義組件。
此文件已根據 Home Assistant 2025.x 開發規範進行了現代化適配。
"""
import logging
import os
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_PORT,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    UnitOfEnergy,
    Platform,
)

from .const import (
    COORDINATOR,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PROTOCOLS,
    STORAGE_PATH,
    UNSUBSCRIBE_LISTENER,
)
from .modbus import ModbusHub

_LOGGER = logging.getLogger(__name__)

# 定義平台列表
PLATFORMS = [Platform.SENSOR]

# 服務名稱和架構定義
SERVICE_RESET_ENERGY = "reset_energy"
RESET_ENERGY_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})


async def async_setup(hass: HomeAssistant, hass_config: dict) -> bool:
    """設置組件的頂層 DOMAIN。"""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """
    非同步設置配置條目（例如：Peacefair 設備）。
    """
    # 關鍵修正: 再次確保 hass.data[DOMAIN] 存在，防止因 setup 時序問題導致的 KeyError
    hass.data.setdefault(DOMAIN, {})

    config = config_entry.data
    options = config_entry.options

    protocol = PROTOCOLS[config[CONF_PROTOCOL]]
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    slave = config[CONF_SLAVE]
    scan_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    # 創建協調器來管理此設備的數據更新。
    coordinator = PeacefairCoordinator(hass, protocol, host, port, slave, scan_interval)

    # 將與此配置條目相關的所有數據存儲在專用字典中
    hass.data[DOMAIN][config_entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    # 第一次數據刷新。
    await coordinator.async_config_entry_first_refresh()

    # 將配置轉發給感測器平台以創建實體。
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # 監聽配置更新。
    unsub = config_entry.add_update_listener(update_listener)
    hass.data[DOMAIN][config_entry.entry_id][UNSUBSCRIBE_LISTENER] = unsub

    # --- 註冊重置電量服務 ---
    def service_handle(service):
        """處理 'reset_energy' 服務調用。"""
        _LOGGER.debug(f"處理重置電量服務調用，目標實體: {service.data.get(ATTR_ENTITY_ID)}")
        coordinator.reset_energy()

    # 檢查服務是否已註冊，避免重複註冊警告
    if not hass.services.has_service(DOMAIN, SERVICE_RESET_ENERGY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_ENERGY,
            service_handle,
            schema=RESET_ENERGY_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """非同步卸載配置條目。"""
    ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    entry_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
    unsub = entry_data.get(UNSUBSCRIBE_LISTENER)

    if unsub:
        unsub()

    if ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

        # 清理文件操作 (保持同步執行以避免複雜性，但捕獲異常)
        def do_blocking_file_operations():
            """執行同步文件刪除操作。"""
            try:
                storage_path = hass.config.path(STORAGE_PATH)
                record_file = hass.config.path(f"{STORAGE_PATH}/{config_entry.entry_id}_state.json")
                reset_file = hass.config.path(f"{STORAGE_PATH}/{DOMAIN}_reset.json")
                
                if os.path.exists(record_file):
                    os.remove(record_file)
                if os.path.exists(reset_file):
                    os.remove(reset_file)
                if os.path.exists(storage_path) and not os.listdir(storage_path):
                    os.rmdir(storage_path)
            except Exception as e:
                _LOGGER.warning(f"清理文件時發生錯誤: {e}")

        await hass.async_add_executor_job(do_blocking_file_operations)

    return ok


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """在運行時處理配置選項更新。"""
    scan_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    
    # 增加檢查以防 entry 尚未完全加載
    if config_entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        coordinator.update_interval = timedelta(seconds=scan_interval)


class PeacefairCoordinator(DataUpdateCoordinator):
    """用於管理 Peacefair 設備數據獲取和輪詢的類。"""

    def __init__(self, hass, protocol, host, port, slave, scan_interval):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({host})",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._hass = hass
        self._host = host
        self._hub = ModbusHub(protocol, host, port, slave)

    @property
    def host(self):
        return self._host

    def reset_energy(self):
        _LOGGER.info(f"正在重置設備 {self._host} 的電量...")
        self._hub.reset_energy()
        if self.data:
            self.data[UnitOfEnergy.KILO_WATT_HOUR] = 0.0
            self.async_set_updated_data(self.data)

    async def _async_update_data(self):
        try:
            data_update = await self._hass.async_add_executor_job(self._hub.info_gather)
            if data_update:
                return data_update
            
            _LOGGER.warning(f"無法從 {self._host} 獲取數據，返回空數據。")
            return self.data if self.data else {}
        except Exception as err:
            _LOGGER.error(f"設備 {self._host} 更新數據時出錯: {err}")
            return self.data if self.data else {}