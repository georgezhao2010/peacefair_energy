# Peacefair Energy Monitor

支持Hass 2025.12.X后版本。

#### [HACS (**点击这里安装**)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gnowmil&repository=peacefair_energy&category=integration)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

[English](https://github.com/gnowmil/peacefair_energy/blob/main/README.md) | 简体中文

使用培正PZEM-004T交流通讯盒进行用电信息采集的Home Assistant集成，支持Home Assistant 2021.8.X后新增的能源功能。

支持通过ModbusRTU over UDP/TCP访问PZEM-004T，不支持串口访问方式。


# 警告

**以下操作仅适于有一定强电电路知识的人，涉及强电操作，注意人身安全。**


# 硬件准备

## 用电信息采集

用电信息采集采用的是培正PZEM-004T，论坛中已有很多解决方案，本方案中采用的是100A使用互感器非接触采集的方案。
非接触采集不用接触强电接线，安全性较好。


## 信息传输

PZEM-004T使用TTL进行通讯，但大老远的拉根USB-TTL线到HA主机，显然不现实，所以这里采用的是WiFi-TTL无线传输模块。
因为PZEM-004T的TTL是5V供电，因此没有直接采用3.3V的ESP-01(S)模块，而是使用了一款基于ESP-M2的DT-06 WiFi-TTL无线传输模块，自带透传固件，5V供电，省掉了5V-3.3V降压模块。当然你可以根据喜好自主选择无线传输模块。

如何配置透传模块，透传模块使用的端口、协议，要记清楚，后续配置要用。


## 接线图

![IMG](https://user-images.githubusercontent.com/27534713/130238853-da93f5c7-105d-4170-be55-89ed83e9f06f.png)


## 接线实拍

照片中是拆掉了弱电箱的门，互感器直接套在入户主线的火线上，从插座的空开下接了一个带USB的小插座，用于给PZEM-004T提供220V/5V供电。看起来乱七八糟，外边挂一幅画就全挡住了。

![IMG](https://user-images.githubusercontent.com/27534713/130238749-2751d491-259b-4974-b838-0bdb550970da.jpg)



PZEM-004T的RX口和DT-06的TX口之间可以考虑串接1K左右电阻，防止PZEM-004T的RX灯常亮

![IMG](https://user-images.githubusercontent.com/27534713/178296051-b32f95df-d317-4697-95ec-6b4754cbf30f.png)


# 集成安装

使用HACS自定义存储库安装，或者从[Latest release](https://github/gnowmil/peacefair_energy/release/latest)下载最新的Release版本，将其中的`custom_components/peacefair_energy`下所有文件放到`<Your Home Assistant Config Folder>/custom_components/peacefair_energy`中，重新启动Home Assistant。


# 配置

## 安装
在Home Assistant的集成界面，点击添加集成，搜索”Peacefair Energy Monitor”进行添加。需要填写的数据包括：
- 透传模块的IP地址
- 透传模块的端口
- 协议(TCP或UDP)
- 模块从站地址(一般为1)


## 选项
选项是采集间隔，默认为15秒钟采集一次，可根据需要自行调整。


# 特性
- 支持Home Assistant之后的能源面板
- 自动记录日、周、月、年度的实时用电量
- 提供昨日、上周、上月、去年的历史用电量

## 误差
根据长期测试，该集成的月度统计数据与国网电力的数据误差低于3%。


## 实时用电信息
实时信息包含以下传感器
| 传感器名称 | 默认名称 |含义 |
| ---- | ---- | ---- |
| sensor.IP_energy | Energy |总用电量 |
| sensor.IP_voltage | Voltage |当前电压 |
| sensor.IP_current | Current |当前电流 |
| sensor.IP_power | Power |当前功率 |
| sensor.IP_frequency | Power Frequency |交流频率 |
| sensor.IP_power_factor | Power Factor |当前功率因数 |


## 统计信息
统计信息包含以下传感器
| 传感器名称 | 默认名称 |含义 |
| ---- | ---- | ---- |
| sensor.IP_day_real | Energy Consumption Today |今日用电量 |
| sensor.IP_day_history | Energy Consumption Yesterday |昨日用电量 |
| sensor.IP_week_real | Energy Consumption This Week |本周用电量 |
| sensor.IP_week_history | Energy Consumption Last Week | 上周用电量 |
| sensor.IP_month_real | Energy Consumption This Month | 本月用电量 |
| sensor.IP_month_history | Energy Consumption Last Month | 上月用电量 |
| sensor.IP_year_real | Energy Consumption This Year | 今年用电量 |
| sensor.IP_year_history | Energy Consumption Last Year | 去年用电量 |


## 服务
包含一个服务

### peacefair_energy.reset_energy

作用为重置总用电量

| 参数 | 描述 | 示例 |
| ---- | ---- | ---- |
| entity_id | 要重置的总用电量实体 | sensor.IP_energy |

*注意：重置总用电量不会影响各实时传感器及统计信息传感器的数值*


# Home Asssitant的能源
在Home Assistant 2021.8.X中新增的能源功能，可以使用集成中的"总用电量"传感器作为能源消耗的统计依据。
如果你是国网北京电力的用户，可以使用[bj_sgcc_energy](https://github.com/georgezhao2010/bj_sgcc_energy)作为电费单价实体。
不是国网北京电力的用户也没关系，可以使用本集成中的本月用电量、今年用电量，根据当地的用电收费政策，使用模版计算出用电单价来。
![IMG](https://user-images.githubusercontent.com/27534713/130241300-1307c9ff-0f10-47f0-bd62-c601a99a0cd9.png)


# 调试
要打开调试日志输出，在configuration.yaml中做如下配置
```
logger:
  default: warn
  logs:
    custom_components.peacefair_energy: debug
```

# 传感器信息显示
以下为示例

![IMG](https://user-images.githubusercontent.com/27534713/130247060-016a8cae-c51e-49ef-9ba5-8a200e835dc9.png)
![IMG](https://user-images.githubusercontent.com/27534713/130249630-5546f8ad-8d98-46b9-8d98-9623dcfe1ff5.png)
![IMG](https://user-images.githubusercontent.com/27534713/130247142-90c200d6-d2f5-4294-83bd-4e1b48031571.png)

