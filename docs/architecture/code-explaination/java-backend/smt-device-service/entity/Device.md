# Device

> 设备实体类，映射 `device` 表，存储 SMT 产线设备基本信息。

**包路径**: `com.smt.platform.device.model.entity`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/model/entity/Device.java`

---

## 类签名

```java
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("device")
public class Device extends BaseEntity
```

**父类**: `BaseEntity`（含 createTime, updateTime, createBy, updateBy, deleted）
**实现接口**: `Serializable`
**表名**: `device`

---

## 字段

| 字段 | 类型 | 修饰符 | 注解 | 说明 |
|------|------|--------|------|------|
| `id` | `Long` | `private` | `@TableId(type = IdType.AUTO)` | 设备 ID，自增主键 |
| `deviceCode` | `String` | `private` | — | 设备编码（全局唯一） |
| `deviceName` | `String` | `private` | — | 设备名称 |
| `deviceType` | `String` | `private` | — | 设备类型：PRINTER/MOUNTER/REFLOW/AOI/SPI/OTHER |
| `productionLine` | `String` | `private` | — | 所属产线 |
| `ipAddress` | `String` | `private` | — | 设备 IP 地址 |
| `protocolType` | `String` | `private` | — | 通信协议类型：OPC_UA/MQTT |
| `opcUaEndpoint` | `String` | `private` | — | OPC UA 端点 URL |
| `status` | `String` | `private` | — | 设备状态：RUNNING/STOPPED/MAINTENANCE |
| `healthScore` | `Integer` | `private` | — | 健康评分（0-100） |

---

## Lombok 生成方法

- 所有字段的 getter/setter
- `equals()`, `hashCode()`, `toString()`

---

## 设备类型枚举值

| 值 | 说明 |
|---|------|
| `PRINTER` | 锡膏印刷机 |
| `MOUNTER` | 贴片机 |
| `REFLOW` | 回流焊 |
| `AOI` | 自动光学检测 |
| `SPI` | 锡膏检测 |
| `OTHER` | 其他 |

## 设备状态枚举值

| 值 | 说明 |
|---|------|
| `RUNNING` | 运行中 |
| `STOPPED` | 已停机 |
| `MAINTENANCE` | 维修中 |
