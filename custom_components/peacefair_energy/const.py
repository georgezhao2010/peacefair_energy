DOMAIN = "peacefair_energy"
DEFAULT_SCAN_INTERVAL = 15
DEFAULT_SLAVE = 1
DEFAULT_PROTOCOL = "ModbusRTU Over UDP/IP"
DEFAULT_PORT = 9000
COORDINATOR = "coordinator"
ENERGY_SENSOR = "energy_sensor"
UN_SUBDISCRIPT = "un_subdiscript"
DEVICE_CLASS_FREQUENCY = "frequency"
DEVICES = "devices"
VERSION = "0.7.6"
GATHER_TIME = "gather_time"
PROTOCOLS = {
    "ModbusRTU Over UDP/IP": "rtuoverudp",
    "ModbusRTU Over TCP/IP": "rtuovertcp"
}

STORAGE_PATH = f".storage/{DOMAIN}"
