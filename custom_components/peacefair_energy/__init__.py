import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import os
from datetime import timedelta
import asyncio
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from .const import(
    DOMAIN,
    COORDINATOR,
    DEFAULT_SCAN_INTERVAL,
    ENERGY_SENSOR,
    UN_SUBDISCRIPT,
    DEVICES,
    PROTOCOLS,
    STORAGE_PATH
)

from homeassistant.const import (
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE,
    UnitOfEnergy
)

from homeassistant.const import ATTR_ENTITY_ID

from .modbus import ModbusHub

SERVICE_RESET_ENERGY = "reset_energy"

RESET_ENERGY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id
    }
)

_LOGGER = logging.getLogger(__name__)


async def update_listener(hass, config_entry):
    scan_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = hass.data[config_entry.entry_id][COORDINATOR]
    coordinator.update_interval = timedelta(seconds=scan_interval)


async def async_setup(hass: HomeAssistant, hass_config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry):
    config = config_entry.data
    protocol = PROTOCOLS[config[CONF_PROTOCOL]]
    _LOGGER.debug(f"protocol={protocol}")
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    slave = config[CONF_SLAVE]
    scan_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if DEVICES not in hass.data[DOMAIN]:
        hass.data[DOMAIN][DEVICES] = []
    hass.data[DOMAIN][DEVICES].append(host)
    if config_entry.entry_id not in hass.data:
        hass.data[config_entry.entry_id] = {}
    coordinator = PeacefairCoordinator(hass, protocol, host, port, slave, scan_interval)
    hass.data[config_entry.entry_id][COORDINATOR] = coordinator
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])
    hass.data[config_entry.entry_id][UN_SUBDISCRIPT] = config_entry.add_update_listener(update_listener)

    async def async_service_handle(service):
        entity_id = service.data[ATTR_ENTITY_ID]
        energy_sensor = next(
            (sensor for sensor in hass.data[DOMAIN][ENERGY_SENSOR] if sensor.entity_id == entity_id),
            None,
        )
        if energy_sensor is None:
            return

        if service.service == SERVICE_RESET_ENERGY:
            coordinator = hass.data[config_entry.entry_id][COORDINATOR]
            if coordinator is not None:
                coordinator.reset_energy()
                await energy_sensor.reset()  # 等待异步方法完成

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_ENERGY,
        async_service_handle,
        schema=RESET_ENERGY_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry):
    await hass.config_entries.async_forward_entry_unloads(config_entry, ["sensor"])

    host = config_entry.data[CONF_HOST]
    host = host.replace(".", "_")
    energy_sensor = next(
        (sensor for sensor in hass.data[DOMAIN][ENERGY_SENSOR] if sensor.entity_id == f"{host}_{DEVICE_CLASS_ENERGY}"),
        None,
    )
    if energy_sensor is not None:
        hass.data[DOMAIN][ENERGY_SENSOR].pop(energy_sensor)
    unsub = hass.data[config_entry.entry_id][UN_SUBDISCRIPT]
    if unsub is not None:
        unsub()
    hass.data.pop(config_entry.entry_id)
    
    # 异步执行文件操作
    storage_path = hass.config.path(f"{STORAGE_PATH}")
    record_file = hass.config.path(f"{STORAGE_PATH}/{config_entry.entry_id}_state.json")
    reset_file = hass.config.path(f"{STORAGE_PATH}/{DOMAIN}_reset.json")
    
    def remove_files():
        if os.path.exists(record_file):
            os.remove(record_file)
        if os.path.exists(reset_file):
            os.remove(reset_file)
        if len(os.listdir(storage_path)) == 0:
            os.rmdir(storage_path)
    
    await hass.async_add_executor_job(remove_files)
    
    return True


class PeacefairCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, protocol, host, port, slave, scan_interval):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval)
        )
        self._updates = None
        self._hass = hass
        self._host = host
        self._hub = ModbusHub(protocol, host, port, slave)

    @property
    def host(self):
        return self._host

    def reset_energy(self):
        self._hub.reset_energy()
        self.data[UnitOfEnergy] = 0.0

    def set_update(self, update):
        self._updates = update

    async def _async_update_data(self):
        data = self.data if self.data is not None else {}
        data_update = await self._hub.info_gather()
        if len(data_update) > 0:
            data = data_update
            _LOGGER.debug(f"Got Data {data}")
            if self._updates is not None:
                # 确保异步方法被正确调用
                if asyncio.iscoroutinefunction(self._updates):
                    await self._updates()
                else:
                    self._updates()
        return data