"""Kafka 事件总线公共模块。

基于 aiokafka 提供异步 producer/consumer，供所有 Agent 复用。
按 AGENTS.md §3.2 要求，禁止在各 Agent 内直接 new kafka client，统一走本模块。
Kafka 不可达时降级为告警日志，不抛未捕获异常，确保主流程不阻塞。
"""

import asyncio
import json
from typing import Awaitable, Callable

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from shared.config import settings
from shared.observability import get_logger

logger = get_logger("kafka_client")


class KafkaClientError(Exception):
    """Kafka 调用异常（已降级，通常不向上抛出）。"""


# ---------------------------------------------------------------------------
# Producer（模块级单例，懒初始化）
# ---------------------------------------------------------------------------

_producer_instance: AIOKafkaProducer | None = None
# producer.start() 是否已成功调用
_producer_started: bool = False
# producer 启动/发送是否曾失败；失败后短路，避免每次 publish 都尝试连接
_producer_failed: bool = False


def _get_producer() -> AIOKafkaProducer | None:
    """获取共享 AIOKafkaProducer 实例（懒初始化，仅构造，不启动）。

    若 settings.kafka_enabled 为 False，返回 None（调用方据此降级）。

    测试时可通过 _reset_producer() 重置后注入 mock。
    """
    global _producer_instance
    if not settings.kafka_enabled:
        return None
    if _producer_instance is None:
        _producer_instance = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
        )
    return _producer_instance


def _reset_producer() -> None:
    """重置共享 producer 单例与状态标记（仅供测试使用）。"""
    global _producer_instance, _producer_started, _producer_failed
    _producer_instance = None
    _producer_started = False
    _producer_failed = False


async def publish(topic: str, value: dict) -> bool:
    """异步发布消息到 Kafka topic。

    Args:
        topic: Kafka topic 名称。
        value: 待发送消息（dict），内部序列化为 JSON。

    Returns:
        True 表示发送成功；False 表示 Kafka 未启用或发送失败（已降级，不抛异常）。
    """
    global _producer_started, _producer_failed

    if not settings.kafka_enabled:
        logger.debug("kafka.publish.skip.disabled", topic=topic)
        return False

    if _producer_failed:
        logger.warning(
            "kafka.publish.skip.producer_failed", topic=topic
        )
        return False

    try:
        producer = _get_producer()
        if producer is None:
            return False
        if not _producer_started:
            await producer.start()
            _producer_started = True
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        await producer.send_and_wait(topic, payload)
        return True
    except Exception as exc:
        # Kafka 不可达或发送失败：标记失败并降级为告警，不向上抛
        _producer_failed = True
        logger.warning(
            "kafka.publish.failed",
            topic=topic,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return False


# ---------------------------------------------------------------------------
# Consumer（后台任务，每个消费者一条 asyncio.Task）
# ---------------------------------------------------------------------------

ConsumerHandler = Callable[[dict], Awaitable[None]]


async def start_consumer(
    topic: str,
    group_id: str,
    handler: ConsumerHandler,
) -> asyncio.Task | None:
    """启动一个 Kafka 消费者后台任务。

    Args:
        topic: 订阅的 Kafka topic。
        group_id: 消费者组 ID。
        handler: 异步消息处理回调，签名 ``async def handler(message: dict) -> None``。

    Returns:
        后台消费任务；Kafka 未启用或启动失败时返回 None（降级，不抛异常）。
    """
    if not settings.kafka_enabled:
        logger.debug("kafka.consumer.skip.disabled", topic=topic)
        return None

    consumer = AIOKafkaConsumer(
        topic,
        group_id=group_id,
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )

    try:
        await consumer.start()
    except Exception as exc:
        # 启动失败：降级为告警，不向上抛，返回 None
        logger.warning(
            "kafka.consumer.start.failed",
            topic=topic,
            group_id=group_id,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return None

    async def _loop() -> None:
        try:
            while True:
                try:
                    partitions = await consumer.getmany(
                        timeout_ms=1000, max_records=100
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    # getmany 运行时错误：记录日志后继续，不退出循环
                    logger.error(
                        "kafka.consumer.getmany.error",
                        topic=topic,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
                    await asyncio.sleep(1)
                    continue

                for _tp, messages in partitions.items():
                    for record in messages:
                        raw = getattr(record, "value", None)
                        if raw is None:
                            continue
                        try:
                            message = json.loads(raw.decode("utf-8"))
                        except (ValueError, UnicodeDecodeError, AttributeError) as exc:
                            logger.warning(
                                "kafka.consumer.parse.failed",
                                topic=topic,
                                error=str(exc),
                            )
                            continue
                        try:
                            await handler(message)
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            # handler 异常：记录日志后继续处理下一条，不退出
                            logger.error(
                                "kafka.consumer.handler.error",
                                topic=topic,
                                error=str(exc),
                                error_type=type(exc).__name__,
                            )
                # 交出控制权，避免空轮询打满事件循环
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass
        finally:
            try:
                await consumer.stop()
            except Exception as exc:
                logger.warning(
                    "kafka.consumer.stop.failed",
                    topic=topic,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

    return asyncio.create_task(_loop())


async def stop_consumer(task: asyncio.Task | None) -> None:
    """优雅停止消费者后台任务（取消任务并关闭 consumer）。

    幂等：传入 None 时直接返回。
    """
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# 生命周期
# ---------------------------------------------------------------------------

async def aclose() -> None:
    """关闭共享 producer（供 FastAPI lifespan shutdown 调用）。

    幂等：producer 未创建或未启动时直接返回。
    """
    global _producer_instance, _producer_started, _producer_failed
    if _producer_instance is not None and _producer_started:
        try:
            await _producer_instance.stop()
        except Exception as exc:
            logger.warning(
                "kafka.producer.stop.failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
    _producer_instance = None
    _producer_started = False
    _producer_failed = False
