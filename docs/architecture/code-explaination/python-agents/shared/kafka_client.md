# kafka_client

> Kafka 事件总线公共模块，基于 aiokafka 提供异步 producer/consumer。

**模块路径**: `shared/kafka_client.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/kafka_client.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `logger` | `BoundLogger` | structlog 日志器 |
| `_producer_instance` | `AIOKafkaProducer \| None` | 共享 producer 单例 |
| `_producer_started` | `bool` | producer 是否已启动 |
| `_producer_failed` | `bool` | producer 启动是否失败 |
| `ConsumerHandler` | `TypeAlias` | `Callable[[dict], Awaitable[None]]` 消费者回调类型 |

---

## 类

### `KafkaClientError(Exception)`

> Kafka 调用异常（已降级，通常不向上抛出）

**签名**: `class KafkaClientError(Exception)`

---

## 顶层函数

### `_get_producer() -> AIOKafkaProducer | None`

> 获取共享 producer 实例

**签名**: `def _get_producer() -> AIOKafkaProducer | None`

**返回值**: `AIOKafkaProducer | None` — 懒初始化的 producer，启动失败返回 None

---

### `_reset_producer() -> None`

> 重置共享 producer（仅供测试）

---

### `async publish(topic: str, value: dict) -> bool`

> 异步发布消息到 Kafka topic

**签名**: `async def publish(topic: str, value: dict) -> bool`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `topic` | `str` | 是 | Kafka topic |
| `value` | `dict` | 是 | 消息内容（自动 JSON 序列化） |

**返回值**: `bool` — 发布是否成功

**逻辑**: 获取 producer → start（如未启动） → send_and_wait → 异常返回 False

---

### `async start_consumer(topic: str, group_id: str, handler: ConsumerHandler) -> asyncio.Task | None`

> 启动 Kafka 消费者后台任务

**签名**: `async def start_consumer(topic: str, group_id: str, handler: ConsumerHandler) -> asyncio.Task | None`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `topic` | `str` | 是 | 消费的 topic |
| `group_id` | `str` | 是 | 消费者组 ID |
| `handler` | `ConsumerHandler` | 是 | 消息处理回调 |

**返回值**: `asyncio.Task | None` — 消费者任务，启动失败返回 None

---

### `async stop_consumer(task: asyncio.Task | None) -> None`

> 优雅停止消费者后台任务

**签名**: `async def stop_consumer(task: asyncio.Task | None) -> None`

---

### `async aclose() -> None`

> 关闭共享 producer

**签名**: `async def aclose() -> None`
