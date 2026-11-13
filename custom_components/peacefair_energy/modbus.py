import logging
from pymodbus.client import ModbusTcpClient, ModbusUdpClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ModbusPDU
from homeassistant.components.sensor import SensorDeviceClass
import pymodbus

_LOGGER = logging.getLogger(__name__)

class ModbusResetEnergyRequest(ModbusPDU):
    """自定義 Modbus 請求，用於功能碼 0x42 (重置電量)。"""

    _rtu_frame_size = 4
    function_code = 0x42

    def __init__(self, **kwargs):
        """初始化請求。"""
        super().__init__(**kwargs)

    def encode(self):
        """編碼請求負載。"""
        return b""

    def get_response_pdu_size(self):
        """返回預期的響應大小。"""
        return 4

    def __str__(self):
        """返回請求的字串表示。"""
        return "ModbusResetEnergyRequest"


class ModbusHub:
    """用於 Peacefair 儀表的 Modbus Hub。"""

    def __init__(self, protocol: str, host: str, port: int, slave: int):
        """初始化 Modbus hub。"""
        self._device_id = slave
        self._protocol = protocol
        self._host = host
        self._port = int(port)
        self._client = None
        
        _LOGGER.debug(f"Pymodbus 版本: {pymodbus.__version__}")
        _LOGGER.debug(f"正在初始化 ModbusHub: {protocol}://{host}:{port}, slave={slave}")

        if protocol == "rtuovertcp":
            self._client = ModbusTcpClient(
                host=self._host,
                port=self._port,
                framer="rtu",
                timeout=5,
            )
        elif protocol == "rtuoverudp":
            self._client = ModbusUdpClient(
                host=self._host,
                port=self._port,
                framer="rtu",
                timeout=5,
            )

    def read_input_registers(self, address: int, count: int):
        """
        從設備讀取輸入寄存器。
        pymodbus 3.13 起參數名為 device_id（slave/unit 已移除）。
        """
        return self._client.read_input_registers(address, count=count, device_id=self._device_id)

    def reset_energy(self):
        """發送重置電量命令。"""
        request = ModbusResetEnergyRequest(dev_id=self._device_id)
        # pymodbus 3.x execute 簽名係 execute(no_response_expected, request)
        self._client.execute(False, request)

    def info_gather(self) -> dict:
        data = {}
        try:
            # 確保連接已建立
            if not self._client.connected:
                _LOGGER.debug("Modbus 客戶端未連接，嘗試連接...")
                self._client.connect()

            # 讀取數據
            result = self.read_input_registers(0, 9)

            # 檢查 Modbus 異常
            if isinstance(result, ModbusIOException):
                _LOGGER.warning(f"Modbus IO 異常: {result}")
                return data
            
            if hasattr(result, "isError") and result.isError():
                _LOGGER.warning(f"Modbus 返回錯誤響應: {result}")
                return data

            if not hasattr(result, "registers"):
                _LOGGER.warning(f"設備響應無效 (無寄存器數據): {result}")
                return data

            if len(result.registers) != 9:
                _LOGGER.warning(f"接收到的寄存器數量不正確: {len(result.registers)} (預期 9)")
                return data

            # 數據解析
            data[SensorDeviceClass.VOLTAGE] = result.registers[0] / 10
            data[SensorDeviceClass.CURRENT] = (
                (result.registers[2] << 16) + result.registers[1]
            ) / 1000
            data[SensorDeviceClass.POWER] = (
                (result.registers[4] << 16) + result.registers[3]
            ) / 10
            data[SensorDeviceClass.ENERGY] = (
                (result.registers[6] << 16) + result.registers[5]
            ) / 1000
            data[SensorDeviceClass.FREQUENCY] = result.registers[7] / 10
            data[SensorDeviceClass.POWER_FACTOR] = result.registers[8] / 100
            
            # _LOGGER.debug(f"數據獲取成功: {data}")

        except Exception as e:
            _LOGGER.error(f"info_gather 執行期間發生異常: {e}", exc_info=True)
            # 發生嚴重錯誤時嘗試關閉連接，以便下次重連
            try:
                self._client.close()
            except:
                pass

        return data