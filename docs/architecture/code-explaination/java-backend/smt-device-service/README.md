# smt-device-service 模块

> 设备管理微服务，提供设备 CRUD、数据采集点管理、OPC UA/MQTT 双通道数据接入、InfluxDB 时序双写和健康评分计算。

**模块路径**: `java-backend/smt-device-service/`
**包根路径**: `com.smt.platform.device`
**端口**: 8081

## 职责

- 设备信息管理（CRUD + 分页查询）
- 采集点管理（创建/列表）
- 设备数据存储（PostgreSQL + InfluxDB 双写）
- OPC UA / MQTT 双协议数据采集
- 设备健康评分计算（基于温度/振动阈值）
- Mock 数据发布（开发环境）

## 包结构

```
com.smt.platform.device/
├── SmtDeviceServiceApplication.java     ← 启动类
├── controller/                          ← REST 控制器
│   ├── DeviceController.java
│   ├── DeviceDataController.java
│   ├── DeviceDataPointController.java
│   └── AuthController.java
├── service/                             ← 业务逻辑接口
│   ├── DeviceService.java
│   ├── DeviceDataService.java
│   └── DeviceDataPointService.java
├── service/impl/                        ← 业务逻辑实现
│   ├── DeviceServiceImpl.java
│   ├── DeviceDataServiceImpl.java
│   └── DeviceDataPointServiceImpl.java
├── model/
│   ├── entity/                          ← 实体类
│   │   ├── Device.java
│   │   ├── DeviceData.java
│   │   └── DeviceDataPoint.java
│   ├── dto/                             ← 数据传输对象
│   │   ├── DeviceCreateDTO.java
│   │   ├── DeviceUpdateDTO.java
│   │   └── DataPointCreateDTO.java
│   └── vo/                              ← 视图对象
│       └── PageVO.java
├── mapper/                              ← MyBatis-Plus Mapper
│   ├── DeviceMapper.java
│   ├── DeviceDataMapper.java
│   └── DeviceDataPointMapper.java
├── collect/                             ← 数据采集
│   ├── DeviceDataCollector.java
│   ├── MqttDataCollector.java
│   ├── opcua/
│   │   ├── OpcUaSubscriber.java
│   │   └── OpcUaProperties.java
│   └── mqtt/
│       └── MqttSubscriberManager.java
├── repository/                          ← 仓储层
│   └── InfluxDBRepository.java
├── health/                              ← 健康评分
│   ├── HealthScoreCalculator.java
│   └── HealthScoreProperties.java
├── config/                              ← 配置类
│   ├── RedisConfig.java
│   ├── InfluxDBConfig.java
│   ├── AsyncConfig.java
│   ├── SlowSqlInterceptor.java
│   ├── MybatisPlusConfig.java
│   └── MockProperties.java
└── mock/                                ← Mock 数据
    └── MockMqttPublisher.java
```

## 依赖关系

- **依赖**: `smt-common`（Result, BizException, JwtUtil, SecurityConfig, BaseEntity 等）
- **外部服务**: PostgreSQL, Redis, InfluxDB, MQTT Broker (Mosquitto), OPC UA Server

## 快速导航

| 包 | 文档 | 说明 |
|---|------|------|
| controller | [DeviceController](controller/DeviceController.md), [DeviceDataController](controller/DeviceDataController.md), [DeviceDataPointController](controller/DeviceDataPointController.md), [AuthController](controller/AuthController.md) | REST 接口 |
| service | [DeviceService](service/DeviceService.md), [DeviceDataService](service/DeviceDataService.md), [DeviceDataPointService](service/DeviceDataPointService.md) | 业务逻辑 |
| entity | [Device](entity/Device.md), [DeviceData](entity/DeviceData.md), [DeviceDataPoint](entity/DeviceDataPoint.md) | 实体类 |
| mapper | [DeviceMapper](mapper/DeviceMapper.md), [DeviceDataMapper](mapper/DeviceDataMapper.md), [DeviceDataPointMapper](mapper/DeviceDataPointMapper.md) | 数据访问 |
| collect | [DeviceDataCollector](collector/DeviceDataCollector.md), [MqttDataCollector](collector/MqttDataCollector.md), [OpcUaSubscriber](collector/OpcUaSubscriber.md), [MqttSubscriberManager](collector/MqttSubscriberManager.md) | 数据采集 |
| repository | [InfluxDBRepository](repository/InfluxDBRepository.md) | 时序数据仓储 |
| health | [HealthScoreCalculator](calculator/HealthScoreCalculator.md) | 健康评分 |
