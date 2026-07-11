# HealthScoreCalculator

> 设备健康评分计算器，基于温度/振动阈值和设备状态计算健康分数。

**包路径**: `com.smt.platform.device.health`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/health/HealthScoreCalculator.java`

---

## 类签名

```java
@Component
public class HealthScoreCalculator
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@Component`

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `log` | `Logger` | `private static final` | SLF4J 日志器 |
| `deviceService` | `DeviceService` | `private final` | 设备服务 |
| `deviceMapper` | `DeviceMapper` | `private final` | 设备 Mapper |
| `deviceDataMapper` | `DeviceDataMapper` | `private final` | 设备数据 Mapper |
| `props` | `HealthScoreProperties` | `private final` | 评分规则配置 |

---

## 构造方法

```java
public HealthScoreCalculator(DeviceService deviceService, DeviceMapper deviceMapper,
                             DeviceDataMapper deviceDataMapper, HealthScoreProperties props)
```

构造器注入所有依赖。

---

## 方法

### `refreshHealthScore(Long deviceId)`

> 刷新指定设备的健康评分

**签名**: `public void refreshHealthScore(Long deviceId)`

**注解**: `@Async("healthScoreExecutor")`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `deviceId` | `Long` | 是 | 设备 ID |

**逻辑**:
1. 查询设备信息
2. 查询最近 N 分钟的数据（由 `recentWindowMinutes` 配置）
3. 调用 `calculate()` 计算评分
4. 更新设备的 `healthScore` 字段

---

### `calculate(Device device, List<DeviceData> recentData)`

> 计算设备健康评分

**签名**: `public int calculate(Device device, List<DeviceData> recentData)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device` | `Device` | 是 | 设备实体 |
| `recentData` | `List<DeviceData>` | 是 | 最近数据列表 |

**返回值**: `int` — 健康评分（0-100）

**评分规则**:

| 设备状态 | 基础评分 | 说明 |
|---------|---------|------|
| MAINTENANCE | 30 | 维修态固定评分 |
| STOPPED | 50 | 停机态固定评分 |
| RUNNING | 100 | 运行态，根据数据扣分 |

**扣分逻辑**（仅 RUNNING 状态）:

| 条件 | 扣分 |
|------|------|
| 温度 > tempThresholdHigh (100°C) | deductionHigh (40分) |
| 温度 > tempThresholdLow (80°C) | deductionLow (20分) |
| 振动 > vibThresholdHigh (20) | deductionHigh (40分) |
| 振动 > vibThresholdLow (10) | deductionLow (20分) |

- 同采集点去重取最新值
- 最终分数 clamp 到 [0, 100]

---

### `isAfter(LocalDateTime cur, LocalDateTime exist)`

> 判断时间是否晚于

**签名**: `private static boolean isAfter(LocalDateTime cur, LocalDateTime exist)`

**返回值**: `boolean` — cur 是否晚于 exist

---

### `tryParseDouble(String s)`

> 安全解析字符串为 double

**签名**: `private static Double tryParseDouble(String s)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `s` | `String` | 待解析字符串 |

**返回值**: `Double` — 解析成功返回值，失败返回 `null`
