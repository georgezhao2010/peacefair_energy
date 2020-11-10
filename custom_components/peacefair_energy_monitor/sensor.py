from homeassistant.const import (
    STATE_UNKNOWN,
    DEVICE_CLASS_VOLTAGE ,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ENERGY ,
    DEVICE_CLASS_POWER_FACTOR,
    VOLT,
    ELECTRICAL_CURRENT_AMPERE,
    POWER_WATT,
    ENERGY_KILO_WATT_HOUR,
    FREQUENCY_HERTZ
)

from .const import(
    DOMAIN,
    MODBUS_HUB,
    IDENT,
    ENERGY_SENSOR,
    DEVICE_CLASS_FREQUENCY
)

from homeassistant.helpers.entity import Entity

HPG_SENSOR_TYPES = [
    DEVICE_CLASS_VOLTAGE ,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ENERGY ,
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
    DEVICE_CLASS_VOLTAGE: VOLT,
    DEVICE_CLASS_CURRENT: ELECTRICAL_CURRENT_AMPERE,
    DEVICE_CLASS_POWER: POWER_WATT,
    DEVICE_CLASS_ENERGY: ENERGY_KILO_WATT_HOUR,
    DEVICE_CLASS_FREQUENCY: FREQUENCY_HERTZ
}

ICONS = {
    DEVICE_CLASS_FREQUENCY: "hass:current-ac"
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    sensors = []
    hub = hass.data[config_entry.entry_id][MODBUS_HUB]
    ident = hass.data[config_entry.entry_id][IDENT]
    for sensortype in HPG_SENSOR_TYPES:
        sensor = HPGSensor(hub, config_entry.entry_id, sensortype, ident)
        sensors.append(sensor)
        if sensor.device_class == sensortype:
            if ENERGY_SENSOR not in hass.data[DOMAIN]:
                hass.data[DOMAIN][ENERGY_SENSOR] = []
            hass.data[DOMAIN][ENERGY_SENSOR].append(sensor)
    async_add_entities(sensors)

class HPGSensor(Entity):
    def __init__(self, hub, entry_id, sensor_type, ident):
        self._state = STATE_UNKNOWN
        self._unique_id = "sensor.{}_{}".format(ident, sensor_type)
        self._entry_id = entry_id
        self.entity_id = self._unique_id
        self._sensor_type = sensor_type
        self._device_info = {
            "identifiers": {(DOMAIN, ident)},
            "manufacturer": "Peacefair",
            "model": "PZEM-004T",
            "name": "Peacefair Power Gather"
        }
        hub.add_update(sensor_type, self.update)

    @property
    def state(self):
        return self._state

    def get_entry_id(self):
        return self._entry_id

    """@property
    def assumed_state(self):
        return False"""

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
    def name(self):
        return NAMES.get(self._sensor_type)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def unit_of_measurement(self):
        return UNITS.get(self._sensor_type)

    @property
    def icon(self):
        return ICONS.get(self._sensor_type)

    def update(self, state):
        self._state = state
        self.schedule_update_ha_state()