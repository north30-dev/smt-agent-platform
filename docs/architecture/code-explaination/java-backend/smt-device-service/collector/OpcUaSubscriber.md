# OpcUaSubscriber

> OPC UA 订阅管理器，负责创建 OPC UA 客户端连接并订阅节点数据变化。

**包路径**: `com.smt.platform.device.collect.opcua`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/collect/opcua/OpcUaSubscriber.java`

---

## 类签名

```java
@Component
public class OpcUaSubscriber
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@Component`

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `log` | `Logger` | `private static final` | SLF4J 日志器 |
| `properties` | `OpcUaProperties` | `private final` | OPC UA 采样参数配置 |
| `clients` | `Map<String, OpcUaClient>` | `private final` | `ConcurrentHashMap`，endpointUrl → client 映射 |

---

## 构造方法

```java
public OpcUaSubscriber(OpcUaProperties properties)
```

构造器注入 `OpcUaProperties`。

---

## 方法

### `subscribe(String endpointUrl, Map<String,String> nodeIdToDatapointCode, Long deviceId, BiConsumer<String,String> callback)`

> 订阅 OPC UA 节点数据变化

**签名**: `public void subscribe(String endpointUrl, Map<String,String> nodeIdToDatapointCode, Long deviceId, BiConsumer<String,String> callback)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `endpointUrl` | `String` | 是 | OPC UA 服务端地址 |
| `nodeIdToDatapointCode` | `Map<String,String>` | 是 | 节点ID → 采集点编码映射 |
| `deviceId` | `Long` | 是 | 设备 ID |
| `callback` | `BiConsumer<String,String>` | 是 | 回调函数（datapointCode, value） |

**逻辑**:
1. 创建 OPC UA Client → 连接到 endpointUrl
2. 创建订阅（publishingInterval, samplingInterval, queueSize）
3. 构建 MonitoredItemCreateRequest 列表
4. 批量创建监控项 → 注册 ItemCreationCallback
5. 数据变化时调用 callback(datapointCode, value)

---

### `disconnect(String endpointUrl)`

> 断开指定 endpoint 的连接

**签名**: `public void disconnect(String endpointUrl)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `endpointUrl` | `String` | 是 | OPC UA 服务端地址 |

**逻辑**: 从 clients map 移除 → disconnect(30s timeout)

---

### `disconnectAll()`

> 断开所有 OPC UA 连接

**签名**: `public void disconnectAll()`

**逻辑**: 遍历所有 endpoint 调用 `disconnect()`

---

### `destroy()`

> Spring 容器销毁时关闭所有连接

**签名**: `public void destroy()`

**注解**: `@PreDestroy`

**逻辑**: 调用 `disconnectAll()`

---

### `buildItemCreationCallback(List<String> datapointCodes, BiConsumer<String,String> callback)`

> 构建监控项创建回调

**签名**: `ItemCreationCallback buildItemCreationCallback(List<String> datapointCodes, BiConsumer<String,String> callback)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `datapointCodes` | `List<String>` | 采集点编码列表（与节点顺序对应） |
| `callback` | `BiConsumer<String,String>` | 数据回调函数 |

**返回值**: `ItemCreationCallback` — 监控项创建回调

**逻辑**: 按 index 匹配 datapointCode → 设置 valueConsumer

---

### `extractValue(DataValue value)`

> 从 OPC UA DataValue 提取字符串值

**签名**: `String extractValue(DataValue value)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `value` | `DataValue` | OPC UA 数据值 |

**返回值**: `String` — 字符串值，null/非 Good 状态返回 `null`

---

### `createClient(String endpointUrl)`

> 工厂方法，创建 OPC UA 客户端

**签名**: `protected OpcUaClient createClient(String endpointUrl)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `endpointUrl` | `String` | OPC UA 服务端地址 |

**返回值**: `OpcUaClient` — OPC UA 客户端实例

**注意**: `protected` 修饰符，可被子类/测试覆写
