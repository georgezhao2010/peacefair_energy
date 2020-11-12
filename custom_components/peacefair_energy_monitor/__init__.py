import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.core import HomeAssistant
from .const import(
    DOMAIN,
    MODBUS_HUB,
    IDENT,
    DEFAULT_SCAN_INTERVAL,
    ENERGY_SENSOR,
    UN_SUBDISCRIPT,
    DEVICES
)

from homeassistant.const import (
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE,
    DEVICE_CLASS_ENERGY
)

from homeassistant.const import ATTR_ENTITY_ID

from .modbus import ModbusGather

SERVICE_RESET_ENERGY = "reset_energy"

RESET_ENERGY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id
    }
)

_LOGGER = logging.getLogger(__name__)

async def update_listener(hass, config_entry):
    hub = hass.data[config_entry.entry_id][MODBUS_HUB]
    scan_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    if hub is not None:
        hub.set_interval(scan_interval)

async def async_setup(hass: HomeAssistant, hass_config: dict):
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.setLevel(logging.DEBUG)
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry):
    config = config_entry.data
    protocol = config[CONF_PROTOCOL]
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    slave = config[CONF_SLAVE]
    scan_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    hub = ModbusGather(hass, slave, protocol, host, port, scan_interval)
    hass.data[DOMAIN][DEVICES] = []
    hass.data[DOMAIN][DEVICES].append("{}_{}".format(host, port))
    hass.data[config_entry.entry_id] = {}
    hass.data[config_entry.entry_id][MODBUS_HUB] = hub
    ident = "{}_{}_{}".format(
        host, port, slave
    )
    ident = ident.replace(".", "_")
    hass.data[config_entry.entry_id][IDENT] = ident
    hub.start_keep_alive()

    hass.async_create_task(hass.config_entries.async_forward_entry_setup(
        config_entry, "sensor"))

    hass.data[config_entry.entry_id][UN_SUBDISCRIPT] = config_entry.add_update_listener(update_listener)

    def service_handle(service):
        entity_id = service.data[ATTR_ENTITY_ID]
        energy_sensor = next(
            (sensor for sensor in hass.data[DOMAIN][ENERGY_SENSOR] if sensor.entity_id == entity_id),
            None,
        )
        if energy_sensor is None:
            _LOGGER.warning("entity is None???".format(energy_sensor))
            return

        if service.service == SERVICE_RESET_ENERGY:
            entry_id = energy_sensor.get_entry_id()
            mhub = hass.data[entry_id][MODBUS_HUB]
            if mhub is not None:
                hass.async_create_task(mhub.async_reset_energy())

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_ENERGY,
        service_handle,
        schema = RESET_ENERGY_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry):

    unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")

    hub = hass.data[config_entry.entry_id][MODBUS_HUB]
    hub.stop_gather()
    ident = hass.data[config_entry.entry_id][IDENT]
    entity_id = "sensor.{}_{}".format(ident, DEVICE_CLASS_ENERGY)
    energy_sensor = next(
        (sensor for sensor in hass.data[DOMAIN][ENERGY_SENSOR] if sensor.entity_id == entity_id),
        None,
    )
    if energy_sensor is not None:
        hass.data[DOMAIN][ENERGY_SENSOR].pop(energy_sensor)
    unsub = hass.data[config_entry.entry_id][UN_SUBDISCRIPT]
    if usub is not None:
        usub()
    hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok