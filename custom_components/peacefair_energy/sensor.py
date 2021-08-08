from homeassistant.const import (
    STATE_UNKNOWN,
    DEVICE_CLASS_VOLTAGE,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER_FACTOR,
    ELECTRIC_POTENTIAL_VOLT,
    ELECTRIC_CURRENT_AMPERE,
    POWER_WATT,
    ENERGY_KILO_WATT_HOUR,
    FREQUENCY_HERTZ
)

from .const import (
    DOMAIN,
    MODBUS_HUB,
    IDENT,
    ENERGY_SENSOR,
    DEVICE_CLASS_FREQUENCY,
    VERSION
)

from homeassistant.helpers.entity import Entity

from homeassistant.util.json import load_json, save_json

import time
import logging

_LOGGER = logging.getLogger(__name__)

RECORD_FILE = f".storage/{DOMAIN}_state.json"

HPG_SENSOR_TYPES = [
    DEVICE_CLASS_VOLTAGE,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER_FACTOR,
    DEVICE_CLASS_FREQUENCY
]

NAMES = {
    DEVICE_CLASS_VOLTAGE: "Peacefair Voltage",
    DEVICE_CLASS_CURRENT: "Peacefair Current",
    DEVICE_CLASS_POWER: "Peacefair Power",
    DEVICE_CLASS_ENERGY: "Peacefair Energy",
    DEVICE_CLASS_POWER_FACTOR: "Peacefair Power Factor",
    DEVICE_CLASS_FREQUENCY: "Peacefair Power Frequency"
}

UNITS = {
    DEVICE_CLASS_VOLTAGE: ELECTRIC_POTENTIAL_VOLT,
    DEVICE_CLASS_CURRENT: ELECTRIC_CURRENT_AMPERE,
    DEVICE_CLASS_POWER: POWER_WATT,
    DEVICE_CLASS_ENERGY: ENERGY_KILO_WATT_HOUR,
    DEVICE_CLASS_POWER_FACTOR: "",
    DEVICE_CLASS_FREQUENCY: FREQUENCY_HERTZ
}

ICONS = {
    DEVICE_CLASS_FREQUENCY: "hass:current-ac"
}

HISTORY_MONTH = "month"
HISTORY_WEEK = "week"
HISTORY_DAY = "day"

HISTORIES = [
    HISTORY_MONTH,
    HISTORY_WEEK,
    HISTORY_DAY
]

HISTORY_NAMES = {
    HISTORY_MONTH: "Energy Consumption Last Month",
    HISTORY_WEEK: "Energy Consumption Last Week",
    HISTORY_DAY: "Energy Consumption Yesterday"
}

REAL_NAMES = {
    HISTORY_MONTH: "Energy Consumption This Month",
    HISTORY_WEEK: "Energy Consumption This Week",
    HISTORY_DAY: "Energy Consumption Today"
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    sensors = []
    hub = hass.data[config_entry.entry_id][MODBUS_HUB]
    ident = hass.data[config_entry.entry_id][IDENT]
    updates = {}
    json_data = load_json(hass.config.path(RECORD_FILE), default={})
    for history_type in HISTORIES:
        state = 0
        if len(json_data) > 0:
            state = json_data[history_type]["history_state"]
        h_sensor = HPGHistorySensor(history_type, DEVICE_CLASS_ENERGY, ident, state)
        sensors.append(h_sensor)
        state = 0
        last_state = 0
        last_time = 0
        if len(json_data) > 0:
            state = json_data[history_type]["real_state"]
            last_state = json_data["last_state"]
            last_time = json_data["last_time"]
        r_sensor = HPGRealSensor(history_type, DEVICE_CLASS_ENERGY, ident, h_sensor, state, last_state, last_time)
        sensors.append(r_sensor)
        updates[history_type] = r_sensor.update_state
    for sensor_type in HPG_SENSOR_TYPES:
        sensor = HPGSensor(hub, config_entry.entry_id, sensor_type, ident, updates)
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
        if self._state == STATE_UNKNOWN:
            return STATE_UNKNOWN
        else:
            return round(self._state, 2)

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
        return UNITS.get(self._sensor_type)

    @property
    def icon(self):
        return ICONS.get(self._sensor_type)


class HPGHistorySensor(HPGBaseSensor):
    def __init__(self, history_type, sensor_type, ident, state):
        super().__init__(sensor_type, ident)
        self._unique_id = f"{DOMAIN}.{ident}_{history_type}_history"
        self.entity_id = self._unique_id
        self._history_type = history_type
        self._state = state

    @property
    def name(self):
        return HISTORY_NAMES.get(self._history_type)

    def update_state(self, state):
        self._state = state
        self.schedule_update_ha_state()


class HPGRealSensor(HPGBaseSensor):
    def __init__(self, history_type, sensor_type, ident, history_sensor, state, last_state, last_time):
        super().__init__(sensor_type, ident)
        self._unique_id = f"{DOMAIN}.{ident}_{history_type}_real"
        self.entity_id = self._unique_id
        self._history_sensor = history_sensor
        self._history_type = history_type
        self._last_state = last_state
        self._last_time = last_time
        self._state = state

    @property
    def name(self):
        return REAL_NAMES.get(self._history_type)

    def update_state(self, cur_time, state):
        differ = state
        last_time = time.localtime(self._last_time)
        current_time = time.localtime(cur_time)

        if state >= self._last_state:
            differ = state - self._last_state
        if (self._history_type == HISTORY_DAY and last_time.tm_mday != current_time.tm_mday) \
                or (self._history_type == HISTORY_WEEK and last_time.tm_wday != current_time.tm_wday and current_time.tm_wday == 0) \
                or (self._history_type == HISTORY_MONTH and last_time.tm_mon != current_time.tm_mon):
            self._history_sensor.update_state(self._state)
            self._state = differ
        else:
            self._state = self._state + differ
        self._last_time = cur_time
        self._last_state = state
        self.schedule_update_ha_state()
        return {
            "history_state": self._history_sensor._state,
            "real_state": self._state
        }


class HPGSensor(HPGBaseSensor):
    def __init__(self, hub, entry_id, sensor_type, ident, energy_updates):
        super().__init__(sensor_type, ident)
        self._unique_id = f"{DOMAIN}.{ident}_{sensor_type}"
        self.entity_id = self._unique_id
        self._entry_id = entry_id
        self._energy_updates = energy_updates
        hub.add_update(sensor_type, self.update_state)

    @property
    def name(self):
        return NAMES.get(self._sensor_type)

    def get_entry_id(self):
        return self._entry_id

    def update_state(self, cur_time, state):
        self._state = state
        self.schedule_update_ha_state()
        if self._sensor_type == DEVICE_CLASS_ENERGY:
            json_data = {"last_time": cur_time, "last_state": state}
            if self._energy_updates is not None:
                for real_type in self._energy_updates:
                    json_data[real_type] = self._energy_updates[real_type](cur_time, state)
                save_json(self.hass.config.path(RECORD_FILE), json_data)

