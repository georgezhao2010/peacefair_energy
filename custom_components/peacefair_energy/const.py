"""Peacefair Energy Monitor 集成的常量。"""

DOMAIN = "peacefair_energy"
VERSION = "0.9.2"

# --- 字典鍵的本地常量 ---
POWER_FACTOR = "power_factor"

# 配置的默認值
DEFAULT_SCAN_INTERVAL = 15
DEFAULT_SLAVE = 1
DEFAULT_PROTOCOL = "ModbusRTU Over UDP/IP"
DEFAULT_PORT = 9000

# --- 階梯電價默認值 ---
DEFAULT_SUMMER_MONTHS = "5,6,7,8,9,10"
DEFAULT_SUMMER_TIER1 = 260
DEFAULT_SUMMER_TIER2 = 600
DEFAULT_NON_SUMMER_TIER1 = 200
DEFAULT_NON_SUMMER_TIER2 = 400

# 夏季電價默認值
DEFAULT_SUMMER_PRICE_L1 = 0.59886875
DEFAULT_SUMMER_PRICE_L2 = 0.64886875
DEFAULT_SUMMER_PRICE_L3 = 0.89886875

# 非夏季電價默認值
DEFAULT_NON_SUMMER_PRICE_L1 = 0.59886875
DEFAULT_NON_SUMMER_PRICE_L2 = 0.64886875
DEFAULT_NON_SUMMER_PRICE_L3 = 0.89886875

# --- 配置鍵 ---
CONF_SUMMER_MONTHS = "summer_months"
CONF_SUMMER_TIER1 = "summer_tier1_limit"
CONF_SUMMER_TIER2 = "summer_tier2_limit"
CONF_NON_SUMMER_TIER1 = "non_summer_tier1_limit"
CONF_NON_SUMMER_TIER2 = "non_summer_tier2_limit"

# 新的價格配置鍵
CONF_SUMMER_PRICE_L1 = "summer_price_level_1"
CONF_SUMMER_PRICE_L2 = "summer_price_level_2"
CONF_SUMMER_PRICE_L3 = "summer_price_level_3"
CONF_NON_SUMMER_PRICE_L1 = "non_summer_price_level_1"
CONF_NON_SUMMER_PRICE_L2 = "non_summer_price_level_2"
CONF_NON_SUMMER_PRICE_L3 = "non_summer_price_level_3"

# 舊的配置鍵 (保留用於遷移或向後兼容，雖然代碼中主要使用新的)
CONF_PRICE_L1 = "price_level_1"
CONF_PRICE_L2 = "price_level_2"
CONF_PRICE_L3 = "price_level_3"

# --- hass.data 存儲的鍵 ---
COORDINATOR = "coordinator"
UNSUBSCRIBE_LISTENER = "unsubscribe_listener"

# --- 協議映射 ---
PROTOCOLS = {
    "ModbusRTU Over UDP/IP": "rtuoverudp",
    "ModbusRTU Over TCP/IP": "rtuovertcp",
}

# --- 存儲路徑 ---
STORAGE_PATH = f".storage/{DOMAIN}"

# --- 其他常量 ---
DEVICE_CLASS_FREQUENCY = "frequency"