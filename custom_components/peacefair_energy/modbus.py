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
        self._param_name = None  # 用於緩存正確的參數名稱 ('slave' 或 'unit')
        
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
        自動適配 pymodbus 的參數名稱 (slave vs unit)。
        """
        # 如果已經知道正確的參數名稱，直接使用
        if self._param_name == 'slave':
            return self._client.read_input_registers(address, count=count, slave=self._device_id)
        elif self._param_name == 'unit':
            return self._client.read_input_registers(address, count=count, unit=self._device_id)
        elif self._param_name == '': # 已確認無參數可用
            return self._client.read_input_registers(address, count=count)

        # 尚未確定參數，嘗試測試
        return self._test_and_read(address, count)

    def _test_and_read(self, address, count):
        """通過試錯法確定正確的參數名稱。"""
        
        # 1. 嘗試 'slave' (新版 pymodbus 標準)
        try:
            # 注意: 如果這裡拋出 TypeError 以外的錯誤 (如 ModbusIOException)，說明參數名稱是正確的，只是通訊失敗
            res = self._client.read_input_registers(address, count=count, slave=self._device_id)
            self._param_name = 'slave'
            _LOGGER.debug("已檢測到 pymodbus 參數名稱: slave")
            return res
        except TypeError as e:
            if "unexpected keyword argument" not in str(e):
                raise e # 如果不是參數錯誤，則拋出異常

        # 2. 嘗試 'unit' (舊版 pymodbus 標準)
        try:
            res = self._client.read_input_registers(address, count=count, unit=self._device_id)
            self._param_name = 'unit'
            _LOGGER.debug("已檢測到 pymodbus 參數名稱: unit")
            return res
        except TypeError as e:
            if "unexpected keyword argument" not in str(e):
                raise e

        # 3. 都失敗，嘗試不帶參數 (依賴默認值)
        _LOGGER.warning("無法確定 read_input_registers 的 slave/unit 參數名稱，將使用默認值進行讀取。")
        self._param_name = '' # 標記為空
        return self._client.read_input_registers(address, count=count)

    def reset_energy(self):
        """發送重置電量命令。"""
        # 嘗試構造請求，分別測試 slave 和 unit
        request = None
        
        # 優先嘗試與 read_input_registers 一致的參數
        if self._param_name == 'slave':
             try:
                 request = ModbusResetEnergyRequest(slave=self._device_id)
             except TypeError: pass
        elif self._param_name == 'unit':
             try:
                 request = ModbusResetEnergyRequest(unit=self._device_id)
             except TypeError: pass

        # 如果上面沒成功或沒緩存，進行試錯
        if not request:
            try:
                request = ModbusResetEnergyRequest(slave=self._device_id)
            except TypeError:
                try:
                    request = ModbusResetEnergyRequest(unit=self._device_id)
                except TypeError:
                    # 如果都不行，嘗試無參數（依賴默認值）
                    request = ModbusResetEnergyRequest()
        
        if request:
            self._client.execute(request)

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