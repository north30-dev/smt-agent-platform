"""Kafka 事件驱动端到端集成测试。

验证 Kafka 消息生产与消费的完整链路。
需要 Kafka + agent-execution 运行。

环境受限时（Kafka 不可达）自动 skip。
"""

import asyncio
import json
import os
import time

import httpx
import pytest

KAFKA_BOOTSTRAP = os.getenv("E2E_KAFKA_BOOTSTRAP", "localhost:9092")
EXECUTION_BASE = os.getenv("E2E_EXECUTION_BASE", "http://localhost:8006")


def _kafka_available() -> bool:
    try:
        from aiokafka import AIOKafkaProducer

        async def _check():
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
            await producer.start()
            await producer.stop()
            return True

        return asyncio.run(_check())
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _skip_if_unavailable():
    if not _kafka_available():
        pytest.skip("Kafka 不可达")


@pytest.mark.integration
def test_kafka_producer_publish_e2e():
    """通过 kafka_client.publish 发送消息 → 验证消息可被消费。"""
    from shared.kafka_client import _reset_producer, publish

    _reset_producer()
    topic = f"e2e-test-{int(time.time())}"
    payload = {"test": True, "timestamp": time.time()}

    async def _run():
        result = await publish(topic, payload)
        assert result is True, "Kafka 消息发送失败"

        from aiokafka import AIOKafkaConsumer

        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id=f"e2e-test-group-{int(time.time())}",
            auto_offset_reset="earliest",
        )
        await consumer.start()
        try:
            records = await asyncio.wait_for(consumer.getmany(timeout_ms=5000, max_records=1), timeout=10.0)
            # getmany returns dict[TopicPartition, list[ConsumerRecord]] or list
            if isinstance(records, dict):
                for tp, msgs in records.items():
                    for msg in msgs:
                        return json.loads(msg.value)
            elif isinstance(records, list):
                for msg in records:
                    return json.loads(msg.value)
        finally:
            await consumer.stop()
        return None

    consumed = asyncio.run(_run())
    assert consumed is not None, "Kafka 消息未被消费到"
    assert consumed["test"] is True
