# MqttSubscriberManager

> MQTT 订阅管理器，封装 Paho MQTT 客户端，提供主题订阅、消息发布和载荷解析能力。

**包路径**: `com.smt.platform.device.collect.mqtt`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/collect/mqtt/MqttSubscriberManager.java`

---

## 类签名

```java
@Component
public class MqttSubscriberManager
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@Component`

---

## 内部类

### `SubscriptionInfo` (private static)

> 订阅信息

| 字段 | 类型 | 说明 |
|------|------|------|
| `deviceId` | `Long` | 设备 ID |
| `datapointCode` | `String` | 采集点编码 |
| `callback` | `BiConsumer<String,String>` | 数据回调函数 |

### `ParsedPayload` (public static)

> 解析后的载荷

| 字段 | 类型 | 说明 |
|------|------|------|
| `value` | `String` | 数据值 |
| `timestamp` | `LocalDateTime` | 时间戳 |

---

## 字段

| 字段 | 类型 | 修饰符 | 注解 | 说明 |
|------|------|--------|------|------|
| `log` | `Logger` | `private static final` | — | SLF4J 日志器 |
| `broker` | `String` | `private final` | `@Value("${smt.mqtt.broker:tcp://localhost:1883}")` | MQTT Broker 地址 |
| `clientIdPrefix` | `String` | `private final` | `@Value("${smt.mqtt.client-id-prefix:smt-device-}")` | 客户端 ID 前缀 |
| `qos` | `int` | `private final` | `@Value("${smt.mqtt.qos:1}")` | QoS 等级 |
| `objectMapper` | `ObjectMapper` | `private final` | — | JSON 序列化器 |
| `subscriptions` | `Map<String, SubscriptionInfo>` | `private final` | — | `ConcurrentHashMap`，topic → 订阅信息 |
| `client` | `MqttClient` | `private` | — | Paho 客户端（懒加载） |

---

## 方法

### `subscribe(String topic, Long deviceId, String datapointCode, BiConsumer<String,String> callback)`

> 订阅 MQTT 主题

**签名**: `public void subscribe(String topic, Long deviceId, String datapointCode, BiConsumer<String,String> callback)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `topic` | `String` | 是 | MQTT 主题 |
| `deviceId` | `Long` | 是 | 设备 ID |
| `datapointCode` | `String` | 是 | 采集点编码 |
| `callback` | `BiConsumer<String,String>` | 是 | 数据回调函数 |

**逻辑**: ensureConnected → client.subscribe(topic, qos) → 注册 SubscriptionInfo

---

### `publish(String topic, String payload)`

> 发布 MQTT 消息

**签名**: `public void publish(String topic, String payload)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `topic` | `String` | 是 | MQTT 主题 |
| `payload` | `String` | 是 | 消息内容 |

**逻辑**: ensureConnected → 构建 MqttMessage → client.publish

---

### `parsePayload(String payload)`

> 解析 MQTT 消息载荷

**签名**: `public ParsedPayload parsePayload(String payload)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `payload` | `String` | MQTT 消息内容 |

**返回值**: `ParsedPayload` — 解析后的值和时间戳

**逻辑**: JSON 解析（value+timestamp 字段）或纯文本处理；null/空返回空值+当前时间

---

### `destroy()`

> Spring 容器销毁时断开 MQTT 连接

**签名**: `public void destroy()`

**注解**: `@PreDestroy`

**逻辑**: 断开 MQTT 连接

---

### `ensureConnected()`

> 懒创建并连接 MQTT 客户端

**签名**: `private synchronized void ensureConnected()`

**逻辑**: 检查 client 是否已连接 → 否则创建 MqttClient + connect → 失败仅日志

---

### `handleMessage(String topic, MqttMessage message)`

> 处理收到的 MQTT 消息

**签名**: `void handleMessage(String topic, MqttMessage message)`

**逻辑**: 按 topic 路由到已注册回调 → parsePayload → callback.accept(datapointCode, value) → 异常不影响后续消息
