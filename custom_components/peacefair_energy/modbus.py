import logging
import asyncio
from pymodbus.client import ModbusTcpClient, ModbusUdpClient
from pymodbus.framer.rtu import FramerRTU
from pymodbus.transaction.transaction import ModbusIOException
from pymodbus.pdu import ModbusPDU
#from pymodbus.exceptions import ModbusException
import threading

try:
    from homeassistant.const import (
        DEVICE_CLASS_VOLTAGE,
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

from .const import (
    DEVICE_CLASS_FREQUENCY
)

HPG_SENSOR_TYPES = [
    DEVICE_CLASS_VOLTAGE,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER_FACTOR,
    DEVICE_CLASS_FREQUENCY
]

_LOGGER = logging.getLogger(__name__)

class ModbusRequest(ModbusPDU):
    """Base class for a modbus request PDU."""

    function_code = -1

    def __init__(self, slave, transaction, skip_encode):
        """Proxy to the lower level initializer.

        :param slave: Modbus slave slave ID
        """
        super().__init__(slave, transaction, skip_encode)
        self.fut = None

    def doException(self, exception):
        """Build an error response based on the function.

        :param exception: The exception to return
        :raises: An exception response
        """
        exc = ExceptionResponse(self.function_code, exception)
        Log.error("Exception response {}", exc)
        return exc

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
        if protocol == "rtuovertcp":
            self._client = ModbusTcpClient(
                host=host,
                port=port,
                framer='rtu',
                timeout=2,
                #retry_on_empty=True,
                #retry_on_invalid=False
            )
        elif protocol == "rtuoverudp":
            self._client = ModbusUdpClient(
                host=host,
                port=port,
                framer='rtu',
                timeout=2,
                #retry_on_empty=False,
                #retry_on_invalid=False
            )

    def connect(self):
        with self._lock:
            self._client.connect()

    def close(self):
        with self._lock:
            self._client.close()

    # 新增同步版本，供线程池调用
    def read_input_registers_sync(self, address, count):
        with self._lock:
            kwargs = {"device_id": self._slave}
            return self._client.read_input_registers(address=address, count=count, **kwargs)

    # 异步版本，交给线程池执行，避免阻塞事件循环
    async def read_input_registers(self, address, count):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self.read_input_registers_sync,
            address,
            count
        )

    def reset_energy(self):
        with self._lock:
            kwargs = {"slave": self._slave}
            request = ModbusResetEnergyRequest(**kwargs)
            self._client.execute(request)

    # 异步版本info_gather
    async def info_gather(self):
        data = {}
        try:
            result = await self.read_input_registers(0, 9)
            if result is not None and type(result) is not ModbusIOException \
                    and result.registers is not None and len(result.registers) == 9:
                data[DEVICE_CLASS_VOLTAGE] = result.registers[0] / 10
                data[DEVICE_CLASS_CURRENT] = ((result.registers[2] << 16) + result.registers[1]) / 1000
                data[DEVICE_CLASS_POWER] = ((result.registers[4] << 16) + result.registers[3]) / 10
                data[DEVICE_CLASS_ENERGY] = ((result.registers[6] << 16) + result.registers[5]) / 1000
                data[DEVICE_CLASS_FREQUENCY] = result.registers[7] / 10
                data[DEVICE_CLASS_POWER_FACTOR] = result.registers[8] / 100
            else:
                _LOGGER.debug("Error in gathering, timed out")
        except Exception as e:
            _LOGGER.error(f"Error in gathering, {e}")
        return data

    # 如果有别的同步读写函数，也建议用类似方式异步包装
