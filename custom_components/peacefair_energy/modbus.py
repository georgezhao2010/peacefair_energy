import logging
from pymodbus.client import ModbusTcpClient, ModbusUdpClient
from pymodbus.transaction import ModbusRtuFramer, ModbusIOException
from pymodbus.pdu import ModbusRequest
import threading
try:
    from homeassistant.const import (
        DEVICE_CLASS_VOLTAGE ,
        DEVICE_CLASS_CURRENT,
        DEVICE_CLASS_POWER,
        DEVICE_CLASS_ENERGY,
        DEVICE_CLASS_POWER_FACTOR
    )
except ImportError:
    DEVICE_CLASS_VOLTAGE = "voltage"
    DEVICE_CLASS_CURRENT = "current"
    DEVICE_CLASS_POWER = "power"
    DEVICE_CLASS_ENERGY = "energy"
    DEVICE_CLASS_POWER_FACTOR = "power_factor"

from .const import(
    DEVICE_CLASS_FREQUENCY
)

HPG_SENSOR_TYPES = [
    DEVICE_CLASS_VOLTAGE ,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ENERGY ,
    DEVICE_CLASS_POWER_FACTOR,
    DEVICE_CLASS_FREQUENCY
]

_LOGGER = logging.getLogger(__name__)

class ModbusResetEnergyRequest(ModbusRequest):
    _rtu_frame_size = 4
    function_code = 0x42
    def __init__(self, **kwargs):
        ModbusRequest.__init__(self, **kwargs)

    def encode(self):
        return b''

    def get_response_pdu_size(self):
        return 4

    def __str__(self):
        return "ModbusResetEnergyRequest"

class ModbusHub:
    def __init__(self, protocol, host, port, slave):
        self._lock = threading.Lock()
        self._slave = slave
        if(protocol == "rtuovertcp"):
            self._client = ModbusTcpClient(
                host = host,
                port = port,
                framer = ModbusRtuFramer,
                timeout = 2,
                retry_on_empty = True,
                retry_on_invalid = False
            )
        elif (protocol == "rtuoverudp"):
            self._client = ModbusUdpClient(
                host = host,
                port = port,
                framer = ModbusRtuFramer,
                timeout = 2,
                retry_on_empty = False,
                retry_on_invalid = False
            )
            
    def connect(self):
        with self._lock:
            self._client.connect()

    def close(self):
        with self._lock:
            self._client.close()

    def read_holding_register(self):
        pass

    def read_input_registers(self, address, count):
        with self._lock:
            kwargs = {"slave": self._slave}
            return self._client.read_input_registers(address, count, **kwargs)

    def reset_energy(self):
        with self._lock:
            kwargs = {"slave": self._slave}
            request = ModbusResetEnergyRequest(**kwargs)
            self._client.execute(request)

    def info_gather(self):
        data = {}
        try:
            result = self.read_input_registers(0, 9)
            if result is not None and type(result) is not ModbusIOException \
                    and result.registers is not None and len(result.registers) == 9:
                data[DEVICE_CLASS_VOLTAGE] = result.registers[0] / 10
                data[DEVICE_CLASS_CURRENT] = ((result.registers[2] << 16) + result.registers[1]) / 1000
                data[DEVICE_CLASS_POWER] = ((result.registers[4] << 16) + result.registers[3]) / 10
                data[DEVICE_CLASS_ENERGY] = ((result.registers[6] << 16) + result.registers[5]) / 1000
                data[DEVICE_CLASS_FREQUENCY] = result.registers[7] / 10
                data[DEVICE_CLASS_POWER_FACTOR] = result.registers[8] / 100
            else:
                _LOGGER.debug(f"Error in gathering, timed out")
        except Exception as e:
            _LOGGER.error(f"Error in gathering, {e}")
        return data
