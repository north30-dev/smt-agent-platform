"""shared.kafka_client 单元测试。

使用 monkeypatch 替换 AIOKafkaProducer / AIOKafkaConsumer 与 settings，
不依赖真实 Kafka broker，覆盖 publish / start_consumer / aclose 的
成功、Kafka 不可达降级、未启用降级、幂等关闭等场景。
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared import kafka_client


def _patch_settings(monkeypatch, **kwargs) -> MagicMock:
    """替换 kafka_client.settings 为可控 mock。

    默认与 shared/config.py 中的 Phase 4 默认值保持一致。
    """
    fake = MagicMock()
    fake.kafka_enabled = kwargs.get("kafka_enabled", True)
    fake.kafka_bootstrap_servers = kwargs.get(
        "kafka_bootstrap_servers", "localhost:9092"
    )
    monkeypatch.setattr(kafka_client, "settings", fake)
    return fake


def _make_producer_mock(
    *,
    start_side_effect=None,
    send_side_effect=None,
) -> MagicMock:
    """构造一个 AIOKafkaProducer 实例 mock。"""
    mock_producer = MagicMock()
    mock_producer.start = AsyncMock(
        side_effect=start_side_effect if start_side_effect is not None else None
    )
    mock_producer.send_and_wait = AsyncMock(
        side_effect=send_side_effect if send_side_effect is not None else None
    )
    mock_producer.stop = AsyncMock()
    return mock_producer


def _make_consumer_mock(
    *,
    start_side_effect=None,
    getmany_return=None,
) -> MagicMock:
    """构造一个 AIOKafkaConsumer 实例 mock。"""
    mock_consumer = MagicMock()
    mock_consumer.start = AsyncMock(
        side_effect=start_side_effect if start_side_effect is not None else None
    )
    mock_consumer.getmany = AsyncMock(
        return_value=getmany_return if getmany_return is not None else {}
    )
    mock_consumer.stop = AsyncMock()
    return mock_consumer


@pytest.fixture(autouse=True)
def _reset_kafka_state():
    """每个用例前后重置 producer 单例与状态标记，避免跨用例污染。"""
    kafka_client._reset_producer()
    yield
    kafka_client._reset_producer()


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------


async def test_publish_success(monkeypatch):
    """成功：producer.start + send_and_wait 均成功，返回 True。"""
    _patch_settings(monkeypatch)
    mock_producer = _make_producer_mock()
    monkeypatch.setattr(
        kafka_client, "AIOKafkaProducer", MagicMock(return_value=mock_producer)
    )

    result = await kafka_client.publish("test.topic", {"key": "value"})

    assert result is True
    mock_producer.start.assert_awaited_once()
    mock_producer.send_and_wait.assert_awaited_once()
    send_args = mock_producer.send_and_wait.call_args.args
    assert send_args[0] == "test.topic"
    assert json.loads(send_args[1].decode("utf-8")) == {"key": "value"}


async def test_publish_kafka_unreachable(monkeypatch):
    """Kafka 不可达：producer.start 抛 ConnectionError，返回 False（不抛异常）。"""
    _patch_settings(monkeypatch)
    mock_producer = _make_producer_mock(
        start_side_effect=ConnectionError("broker unreachable")
    )
    monkeypatch.setattr(
        kafka_client, "AIOKafkaProducer", MagicMock(return_value=mock_producer)
    )

    result = await kafka_client.publish("test.topic", {"key": "value"})

    assert result is False
    mock_producer.start.assert_awaited_once()
    # 启动失败后不应继续调用 send_and_wait
    mock_producer.send_and_wait.assert_not_awaited()


async def test_publish_send_failure_returns_false(monkeypatch):
    """send_and_wait 抛异常时同样降级返回 False。"""
    _patch_settings(monkeypatch)
    mock_producer = _make_producer_mock(
        send_side_effect=RuntimeError("send failed")
    )
    monkeypatch.setattr(
        kafka_client, "AIOKafkaProducer", MagicMock(return_value=mock_producer)
    )

    result = await kafka_client.publish("test.topic", {"key": "value"})

    assert result is False


async def test_publish_disabled(monkeypatch):
    """kafka_enabled=False 时 publish 立即返回 False，不创建 producer。"""
    _patch_settings(monkeypatch, kafka_enabled=False)
    producer_cls = MagicMock()
    monkeypatch.setattr(kafka_client, "AIOKafkaProducer", producer_cls)

    result = await kafka_client.publish("test.topic", {"key": "value"})

    assert result is False
    producer_cls.assert_not_called()


async def test_publish_reuses_started_producer(monkeypatch):
    """第二次 publish 复用已启动的 producer，不重复 start。"""
    _patch_settings(monkeypatch)
    mock_producer = _make_producer_mock()
    monkeypatch.setattr(
        kafka_client, "AIOKafkaProducer", MagicMock(return_value=mock_producer)
    )

    first = await kafka_client.publish("test.topic", {"i": 1})
    second = await kafka_client.publish("test.topic", {"i": 2})

    assert first is True
    assert second is True
    # start 只应调用一次
    mock_producer.start.assert_awaited_once()
    assert mock_producer.send_and_wait.await_count == 2


async def test_publish_short_circuits_after_failure(monkeypatch):
    """首次失败后再次 publish 应短路返回 False，不重试连接。"""
    _patch_settings(monkeypatch)
    mock_producer = _make_producer_mock(
        start_side_effect=ConnectionError("broker down")
    )
    monkeypatch.setattr(
        kafka_client, "AIOKafkaProducer", MagicMock(return_value=mock_producer)
    )

    first = await kafka_client.publish("test.topic", {"i": 1})
    second = await kafka_client.publish("test.topic", {"i": 2})

    assert first is False
    assert second is False
    # 失败后短路：start 只被调用一次（第二次未再尝试）
    mock_producer.start.assert_awaited_once()


# ---------------------------------------------------------------------------
# start_consumer / stop_consumer
# ---------------------------------------------------------------------------


async def test_start_consumer_success(monkeypatch):
    """成功：返回 asyncio.Task，consumer.start 已被调用。"""
    _patch_settings(monkeypatch)
    mock_consumer = _make_consumer_mock(getmany_return={})
    monkeypatch.setattr(
        kafka_client, "AIOKafkaConsumer", MagicMock(return_value=mock_consumer)
    )
    handler = AsyncMock()

    task = await kafka_client.start_consumer("test.topic", "test-group", handler)

    assert task is not None
    assert isinstance(task, asyncio.Task)
    mock_consumer.start.assert_awaited_once()

    # 交出控制权让后台循环跑一轮
    await asyncio.sleep(0.05)
    await kafka_client.stop_consumer(task)

    # 关闭时应调用 consumer.stop
    mock_consumer.stop.assert_awaited()


async def test_start_consumer_kafka_unreachable(monkeypatch):
    """consumer.start 抛异常时返回 None，不创建后台任务。"""
    _patch_settings(monkeypatch)
    mock_consumer = _make_consumer_mock(
        start_side_effect=ConnectionError("broker unreachable")
    )
    monkeypatch.setattr(
        kafka_client, "AIOKafkaConsumer", MagicMock(return_value=mock_consumer)
    )
    handler = AsyncMock()

    task = await kafka_client.start_consumer("test.topic", "test-group", handler)

    assert task is None
    mock_consumer.start.assert_awaited_once()
    handler.assert_not_awaited()


async def test_start_consumer_disabled(monkeypatch):
    """kafka_enabled=False 时 start_consumer 立即返回 None。"""
    _patch_settings(monkeypatch, kafka_enabled=False)
    consumer_cls = MagicMock()
    monkeypatch.setattr(kafka_client, "AIOKafkaConsumer", consumer_cls)

    task = await kafka_client.start_consumer(
        "test.topic", "test-group", AsyncMock()
    )

    assert task is None
    consumer_cls.assert_not_called()


def _one_shot_getmany(partitions):
    """返回一个 getmany 协程函数：仅首次返回 partitions，其后返回空 dict。

    模拟 Kafka 一次性投递，避免循环重复消费同一条消息导致断言失败。
    """
    state = {"delivered": False}

    async def _fake_getmany(*_args, **_kwargs):
        if not state["delivered"]:
            state["delivered"] = True
            return partitions
        return {}

    return _fake_getmany


async def test_start_consumer_invokes_handler(monkeypatch):
    """消费循环应解析 JSON 并调用 handler。"""
    _patch_settings(monkeypatch)

    # 构造一条 ConsumerRecord-like 对象
    record = MagicMock()
    record.value = json.dumps({"device_id": 1, "status": "ALERT"}).encode("utf-8")

    partition = MagicMock()
    partitions = {partition: [record]}
    mock_consumer = _make_consumer_mock()
    mock_consumer.getmany = _one_shot_getmany(partitions)
    monkeypatch.setattr(
        kafka_client, "AIOKafkaConsumer", MagicMock(return_value=mock_consumer)
    )
    handler = AsyncMock()

    task = await kafka_client.start_consumer("test.topic", "test-group", handler)

    assert task is not None
    # 等待循环处理消息
    await asyncio.sleep(0.1)
    await kafka_client.stop_consumer(task)

    handler.assert_awaited_once()
    assert handler.call_args.args[0] == {"device_id": 1, "status": "ALERT"}


async def test_start_consumer_handler_error_continues(monkeypatch):
    """handler 抛异常时循环应继续，不退出后台任务。"""
    _patch_settings(monkeypatch)

    record = MagicMock()
    record.value = json.dumps({"i": 1}).encode("utf-8")
    partition = MagicMock()
    partitions = {partition: [record]}
    mock_consumer = _make_consumer_mock()
    mock_consumer.getmany = _one_shot_getmany(partitions)
    monkeypatch.setattr(
        kafka_client, "AIOKafkaConsumer", MagicMock(return_value=mock_consumer)
    )
    handler = AsyncMock(side_effect=ValueError("handler boom"))

    task = await kafka_client.start_consumer("test.topic", "test-group", handler)
    assert task is not None

    await asyncio.sleep(0.1)
    # 任务不应因 handler 异常而退出
    assert not task.done()
    await kafka_client.stop_consumer(task)


async def test_stop_consumer_none_is_noop():
    """stop_consumer(None) 应直接返回，不抛异常。"""
    await kafka_client.stop_consumer(None)


async def test_stop_consumer_cancels_task(monkeypatch):
    """stop_consumer 应取消后台任务。"""
    _patch_settings(monkeypatch)
    mock_consumer = _make_consumer_mock(getmany_return={})
    monkeypatch.setattr(
        kafka_client, "AIOKafkaConsumer", MagicMock(return_value=mock_consumer)
    )

    task = await kafka_client.start_consumer(
        "test.topic", "test-group", AsyncMock()
    )
    await asyncio.sleep(0.05)

    await kafka_client.stop_consumer(task)

    assert task.cancelled() or task.done()


# ---------------------------------------------------------------------------
# aclose
# ---------------------------------------------------------------------------


async def test_aclose_idempotent():
    """aclose 在未初始化任何 producer 时调用不应抛异常。"""
    # 未做任何 publish，producer 单例为 None
    await kafka_client.aclose()


async def test_aclose_closes_started_producer(monkeypatch):
    """aclose 关闭已启动的 producer，并重置单例。"""
    _patch_settings(monkeypatch)
    mock_producer = _make_producer_mock()
    monkeypatch.setattr(
        kafka_client, "AIOKafkaProducer", MagicMock(return_value=mock_producer)
    )

    # 先 publish 触发 start
    await kafka_client.publish("test.topic", {"k": "v"})
    assert mock_producer.start.await_count == 1

    await kafka_client.aclose()
    mock_producer.stop.assert_awaited_once()
    # aclose 后单例应被重置
    assert kafka_client._producer_instance is None
    assert kafka_client._producer_started is False


async def test_aclose_after_failure_does_not_call_stop(monkeypatch):
    """producer 启动失败后 aclose 不应调用 stop（producer 未启动）。"""
    _patch_settings(monkeypatch)
    mock_producer = _make_producer_mock(
        start_side_effect=ConnectionError("broker down")
    )
    monkeypatch.setattr(
        kafka_client, "AIOKafkaProducer", MagicMock(return_value=mock_producer)
    )

    await kafka_client.publish("test.topic", {"k": "v"})  # 失败
    await kafka_client.aclose()

    mock_producer.stop.assert_not_awaited()
