import logging

from pymodbus.client.sync import ModbusTcpClient, ModbusUdpClient, ModbusSerialClient
from pymodbus.transaction import ModbusRtuFramer, ModbusIOException
from pymodbus.pdu import ModbusRequest
import threading
import time

from homeassistant.const import (
    DEVICE_CLASS_VOLTAGE ,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER_FACTOR
)

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
    def __init__(self, protocol, host, port):
        self._lock = threading.Lock()
        if(protocol == "rtuovertcp"):
            self._client = ModbusTcpClient(
                host = host,
                port = port,
                framer = ModbusRtuFramer,
                timeout = 2,
                retry_on_empty = True,
            )
        elif (protocol == "rtuoverudp"):
            self._client = ModbusUdpClient(
                host = host,
                port = port,
                framer = ModbusRtuFramer,
                timeout = 2,
                retry_on_empty = True,
            )
            
    def connect(self):
        with self._lock:
            self._client.connect()

    def close(self):
        with self._lock:
            self._client.close()

    def read_holding_register(self):
        pass

    def read_input_registers(self, slave, address, count):
        with self._lock:
            kwargs = {"unit": slave} if self else {}
            return self._client.read_input_registers(address, count, **kwargs)

    def reset_energy(self, slave):
        with self._lock:
            kwargs = {"unit": slave} if self else {}
            request = ModbusResetEnergyRequest(**kwargs)
            self._client.execute(request)

class ModbusGather(ModbusHub, threading.Thread):
    def __init__(self, hass, slave, protocol, host, port, scan_interval):
        ModbusHub.__init__(self, protocol, host, port)
        threading.Thread.__init__(self)
        self._entity_id_base = "{}_{}_{}".format(
            host, port, slave
        )
        self._hass = hass
        self._entity_id_base = self._entity_id_base.replace(".", "_")
        self._slave = slave
        self._run = False
        self._interval = scan_interval
        self._updates = {}

    def infogather(self):

        result = self.read_input_registers(self._slave, 0, 9)
        if result is not None and type(result) is not ModbusIOException \
                and result.registers is not None and len(result.registers) == 9:
            data = {}

            data[DEVICE_CLASS_VOLTAGE] = result.registers[0] / 10
            data[DEVICE_CLASS_CURRENT] = ((result.registers[2] << 16) + result.registers[1]) / 1000
            data[DEVICE_CLASS_POWER] = ((result.registers[4] << 16) + result.registers[3]) / 10
            data[DEVICE_CLASS_ENERGY] = (result.registers[6] << 16) + result.registers[5] / 1000
            data[DEVICE_CLASS_FREQUENCY] = result.registers[7] / 10
            data[DEVICE_CLASS_POWER_FACTOR] = result.registers[8] / 100
            for sensor_type in HPG_SENSOR_TYPES:
                if sensor_type in data:
                    update_handle = self._updates[sensor_type]
                    if update_handle is not None:
                        update_handle(data[sensor_type])

    def run(self):
        self.connect()
        counter = 0
        while self._run:
            counter = counter + 1
            if counter >= self._interval:
                self.infogather()
                counter = 0
            time.sleep(1)

        self._client.close()

    def start_keep_alive(self):
        self._run = True
        threading.Thread.start(self)

    def stop_gather(self):
        self._run = False
        threading.Thread.stop(self)
        threading.Thread.join(self)

    async def async_reset_energy(self):
        self.reset_energy(self._slave)

    def set_interval(self, interval):
        self._interval = interval

    def add_update(self, sensor_type, handler):
        self._updates[sensor_type] = handler

