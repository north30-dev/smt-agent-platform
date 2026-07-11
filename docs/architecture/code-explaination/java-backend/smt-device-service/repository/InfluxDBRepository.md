# InfluxDBRepository

> InfluxDB 时序数据仓储，负责将设备数据写入 InfluxDB 进行双写。

**包路径**: `com.smt.platform.device.repository`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/repository/InfluxDBRepository.java`

---

## 类签名

```java
@Slf4j
@Component
public class InfluxDBRepository
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@Slf4j`, `@Component`

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `influxDBClient` | `InfluxDBClient` | `private final` | InfluxDB 客户端 |
| `bucket` | `String` | `private final` | 存储桶名称 |
| `orgName` | `String` | `private final` | InfluxDB 组织名称 |

---

## 构造方法

```java
public InfluxDBRepository(
    InfluxDBClient influxDBClient,
    @Value("${smt.influxdb.bucket:device_data}") String bucket,
    @Value("${smt.influxdb.org-name:smt}") String orgName
)
```

构造器注入 + 配置值绑定。

---

## 方法

### `writeDeviceData(Long deviceId, String datapointCode, String value, LocalDateTime timestamp)`

> 写入一条设备数据到 InfluxDB

**签名**: `public void writeDeviceData(Long deviceId, String datapointCode, String value, LocalDateTime timestamp)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `deviceId` | `Long` | 是 | 设备 ID |
| `datapointCode` | `String` | 是 | 采集点编码 |
| `value` | `String` | 是 | 数据值 |
| `timestamp` | `LocalDateTime` | 是 | 数据采集时间 |

**逻辑**:
1. 构建 InfluxDB Point：
   - measurement: `device_data`
   - tags: `device_id` (string), `datapoint_code`
   - field: `value`
   - timestamp: 指定时间
2. 调用 `writePoint()` 写入
3. 异常仅 warn 日志，不向上抛出（不影响主流程）

**注意事项**:
- 写入失败不会影响 PostgreSQL 的主数据存储
- 异常被静默处理，仅记录日志
