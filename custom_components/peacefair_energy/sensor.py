from homeassistant.components.sensor import (
    SensorDeviceClass
)
from homeassistant.const import (
    STATE_UNKNOWN,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfFrequency
)
from .const import (
    DOMAIN,
    COORDINATOR,
    ENERGY_SENSOR,
    VERSION,
    STORAGE_PATH
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import Entity
from homeassistant.util.json import load_json
from homeassistant.helpers.json import save_json
from typing import final, Final
import time
import logging
import os
import datetime
import asyncio

_LOGGER = logging.getLogger(__name__)


HPG_SENSORS = {
    SensorDeviceClass.VOLTAGE: {
        "name": "Voltage",
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": "measurement"
    },
    SensorDeviceClass.CURRENT: {
        "name": "Current",
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": "measurement"
    },
    SensorDeviceClass.POWER: {
        "name": "Power",
        "unit": UnitOfPower.WATT,
        "state_class": "measurement"
    },
    SensorDeviceClass.ENERGY: {
        "name": "Energy",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": "total_increasing"
    },
    SensorDeviceClass.POWER_FACTOR: {
        "name": "Power Factor",
        "state_class": "measurement"
    },
    SensorDeviceClass.FREQUENCY: {
        "name": "Power Frequency",
        "unit": UnitOfFrequency.HERTZ,
        "icon": "hass:current-ac",
        "state_class": "measurement"
    },
}

HISTORY_YEAR = "year"
HISTORY_MONTH = "month"
HISTORY_WEEK = "week"
HISTORY_DAY = "day"

HISTORIES = {
    HISTORY_YEAR: {
        "history_name": "Energy Consumption Last Year",
        "real_name": "Energy Consumption This Year",
    },
    HISTORY_MONTH: {
        "history_name": "Energy Consumption Last Month",
        "real_name": "Energy Consumption This Month",
    },
    HISTORY_WEEK: {
        "history_name": "Energy Consumption Last Week",
        "real_name": "Energy Consumption This Week",
    },
    HISTORY_DAY:{
        "history_name": "Energy Consumption Yesterday",
        "real_name": "Energy Consumption Today",
    }
}
ATTR_LAST_RESET: Final = "last_reset"
ATTR_STATE_CLASS: Final = "state_class"


async def async_setup_entry(hass, config_entry, async_add_entities):
    sensors = []
    coordinator = hass.data[config_entry.entry_id][COORDINATOR]
    ident = coordinator.host.replace(".", "_")
    updates = {}
    # 创建目录（使用异步执行器运行）
    def _ensure_dir():
        os.makedirs(hass.config.path(STORAGE_PATH), exist_ok=True)
    await hass.async_add_executor_job(_ensure_dir)

    record_file = hass.config.path(f"{STORAGE_PATH}/{config_entry.entry_id}_state.json")
    reset_file = hass.config.path(f"{STORAGE_PATH}/{DOMAIN}_reset.json")
    
    # 异步加载JSON数据
    json_data = await hass.async_add_executor_job(load_json, record_file, {})
    reset_json_data = await hass.async_add_executor_job(load_json, reset_file, {})
    
    for history_type in HISTORIES.keys():
        # 修复：检查键是否存在，使用默认值
        history_data = json_data.get(history_type, {})
        state = history_data.get("history_state", STATE_UNKNOWN)
        _LOGGER.debug(f"Load {history_type} history data {state}")
        h_sensor = HPGHistorySensor(history_type, SensorDeviceClass.ENERGY, ident, state)
        sensors.append(h_sensor)
        
        # 修复：检查键是否存在，使用默认值
        state = history_data.get("real_state", STATE_UNKNOWN)
        last_state = json_data.get("last_state", STATE_UNKNOWN)
        last_time = json_data.get("last_time", 0)
        
        r_sensor = HPGRealSensor(history_type, SensorDeviceClass.ENERGY, ident, h_sensor, state, last_state, last_time, hass, record_file)
        sensors.append(r_sensor)
        updates[history_type] = r_sensor.async_update_state  # 使用异步方法

    # 修复：检查键是否存在，使用默认值
    last_reset = reset_json_data.get("last_reset", 0) if reset_json_data else 0
    
    for sensor_type in HPG_SENSORS.keys():
        sensor = HPGSensor(coordinator, config_entry.entry_id, sensor_type, ident, updates, last_reset, hass, reset_file)
        sensors.append(sensor)
        if sensor.device_class == sensor_type:
            if ENERGY_SENSOR not in hass.data[DOMAIN]:
                hass.data[DOMAIN][ENERGY_SENSOR] = []
            hass.data[DOMAIN][ENERGY_SENSOR].append(sensor)
    async_add_entities(sensors)


class HPGBaseSensor(Entity):
    def __init__(self, sensor_type, ident):
        self._state = STATE_UNKNOWN
        self._sensor_type = sensor_type
        self._device_info = {
            "identifiers": {(DOMAIN, ident)},
            "manufacturer": "Peacefair",
            "model": "PZEM-004T",
            "sw_version": VERSION,
            "name": "Peacefair Energy Monitor"
        }

    @property
    def state(self):
        return STATE_UNKNOWN if self._state == STATE_UNKNOWN else round(self._state, 2)

    @property
    def should_poll(self):
        return False

    @property
    def device_info(self):
        return self._device_info

    @property
    def device_class(self):
        return self._sensor_type

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def unit_of_measurement(self):
        return HPG_SENSORS[self._sensor_type].get("unit")

    @property
    def icon(self):
        return HPG_SENSORS[self._sensor_type].get("icon")

    @property
    def state_class(self):
        return HPG_SENSORS[self._sensor_type].get("state_class")

    @property
    def capability_attributes(self):
        return {ATTR_STATE_CLASS: self.state_class} if self.state_class else {}


class HPGHistorySensor(HPGBaseSensor):
    def __init__(self, history_type, sensor_type, ident, state):
        super().__init__(sensor_type, ident)
        self._unique_id = f"{DOMAIN}.{ident}_{history_type}_history"
        self.entity_id = self._unique_id
        self._history_type = history_type
        self._state = state

    @property
    def name(self):
        return HISTORIES[self._history_type].get("history_name")

    async def async_update_state(self, state):
        self._state = state
        self.async_write_ha_state()


class HPGRealSensor(HPGBaseSensor):
    def __init__(self, history_type, sensor_type, ident, history_sensor, state, last_state, last_time, hass, record_file):
        super().__init__(sensor_type, ident)
        self._unique_id = f"{DOMAIN}.{ident}_{history_type}_real"
        self.entity_id = self._unique_id
        self._history_sensor = history_sensor
        self._history_type = history_type
        self._last_state = last_state
        self._last_time = last_time
        self._state = state
        self.hass = hass
        self._record_file = record_file

    @property
    def name(self):
        return HISTORIES[self._history_type].get("real_name")

    async def async_update_state(self, cur_time, state):
        if state != STATE_UNKNOWN and self._last_state != STATE_UNKNOWN:
            differ = state
            last_time = time.localtime(self._last_time)
            current_time = time.localtime(cur_time)
            if state >= self._last_state:
                differ = round(state - self._last_state, 3)
            if (self._history_type == HISTORY_DAY and last_time.tm_mday != current_time.tm_mday) \
                    or (self._history_type == HISTORY_WEEK and last_time.tm_wday != current_time.tm_wday and current_time.tm_wday == 0) \
                    or (self._history_type == HISTORY_MONTH and last_time.tm_mon != current_time.tm_mon)\
                    or (self._history_type == HISTORY_YEAR and last_time.tm_year != current_time.tm_year):
                await self._history_sensor.async_update_state(self._state)
                self._state = differ
            elif self._state == STATE_UNKNOWN:
                self._state = differ
            else:
                self._state = self._state + differ
        self._last_time = cur_time
        self._last_state = state
        self.async_write_ha_state()
        
        # 修复：加载现有数据，然后更新特定历史类型的数据
        current_data = await self.hass.async_add_executor_job(load_json, self._record_file, {})
        if not current_data:
            current_data = {}
            
        # 更新当前历史类型的数据
        if self._history_type not in current_data:
            current_data[self._history_type] = {}
            
        current_data[self._history_type]["history_state"] = self._history_sensor._state
        current_data[self._history_type]["real_state"] = self._state
        current_data["last_time"] = cur_time
        current_data["last_state"] = state
        
        # 异步保存
        await self.hass.async_add_executor_job(
            save_json,
            self._record_file,
            current_data
        )
        return {
            "history_state": self._history_sensor._state,
            "real_state": self._state
        }


class HPGSensor(CoordinatorEntity, HPGBaseSensor):
    def __init__(self, coordinator, entry_id, sensor_type, ident, energy_updates, last_reset, hass, reset_file):
        super().__init__(coordinator)
        HPGBaseSensor.__init__(self, sensor_type, ident)
        self._unique_id = f"{DOMAIN}.{ident}_{sensor_type}"
        self.entity_id = self._unique_id
        self._energy_updates = energy_updates
        self._last_reset = datetime.datetime.fromtimestamp(last_reset)
        self._record_file = hass.config.path(f"{STORAGE_PATH}/{entry_id}_state.json")
        self._reset_file = reset_file
        self.hass = hass
        if self._sensor_type == SensorDeviceClass.ENERGY:
            coordinator.set_update(self.async_update_state)

    @property
    def state(self):
        if self._sensor_type in self.coordinator.data:
            return round(self.coordinator.data[self._sensor_type], 2)
        else:
            return STATE_UNKNOWN

    @property
    def name(self):
        return HPG_SENSORS[self._sensor_type].get("name")

    async def async_update_state(self):
        cur_time = time.time()
        json_data = {"last_time": cur_time, "last_state": self.state}
        if self._energy_updates is not None:
            for real_type in self._energy_updates:
                update_result = await self._energy_updates[real_type](cur_time, self.state)
                json_data[real_type] = update_result
            # 异步保存
            await self.hass.async_add_executor_job(
                save_json,
                self._record_file,
                json_data
            )

    @property
    def last_reset(self):
        return self._last_reset if self._sensor_type == SensorDeviceClass.ENERGY else None

    @final
    @property
    def state_attributes(self):
        return {ATTR_LAST_RESET: self.last_reset.isoformat()} if self._sensor_type == SensorDeviceClass.ENERGY else {}

    async def async_reset(self):
        self._last_reset = datetime.datetime.now()
        json_data = {"last_reset": self._last_reset.timestamp()}
        _LOGGER.debug(f"Energy reset")
        # 异步保存
        await self.hass.async_add_executor_job(
            save_json,
            self._reset_file,
            json_data
        )