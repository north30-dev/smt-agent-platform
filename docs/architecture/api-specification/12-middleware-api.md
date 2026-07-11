# 中间件服务接口

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 十二、中间件服务接口

### 12.1 PostgreSQL

**连接信息**:

```
Host: localhost (docker: smt-postgres)
Port: 5432
Database: smt
User: smt
Password: smt123
```

**关键表结构**:

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| device | 设备台账 | device_code, device_name, health_score |
| production_orders | 订单数据 | order_no, priority, status |
| quality_alerts | 质量告警 | alert_no, severity, defect_rate |

### 12.2 Redis

**连接信息**:

```
Host: localhost (docker: smt-redis)
Port: 6380
Password: root
```

**用途**: 会话存储、缓存设备数据、Agent状态缓存

### 12.3 InfluxDB

**连接信息**:

```
Host: http://localhost:8086
Org: smt
Bucket: device_data
Token: <redacted>
```

**用途**: 设备时序数据存储、传感器数据、健康评分历史记录

### 12.4 Milvus

**连接信息**:

```
Host: localhost (docker: smt-milvus)
Port: 19530
```

**用途**: 知识案例向量检索、历史案例相似度匹配、RAG知识库

### 12.5 MinIO

**连接信息**:

```
Host: http://localhost:9000
Console: http://localhost:9001
```

**用途**: Milvus 对象存储后端、文件存储

### 12.6 Mosquitto MQTT

**连接信息**:

```
Host: localhost
Port: 1883
协议: MQTT
```

**用途**: 设备遥测数据接入、Mock 设备数据上报
