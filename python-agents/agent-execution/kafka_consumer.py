"""Kafka device.anomaly 消费者。

消费设备异常事件 → 调用 orchestrator device_fault 接口 → 自动生成执行指令。
遵循 agent-orchestrator/agent_clients.py 的模块级 httpx.AsyncClient 单例模式。
Kafka 不可达时由 shared.kafka_client 降级为日志，本模块不抛异常。
消息处理失败时记录异常记录（exception_records），不向上抛、不退出消费循环。

orchestrator 基地址在 config.py 中无对应字段，使用模块常量 ORCHESTRATOR_URL。
"""

import asyncio

import httpx

from shared.config import settings
from shared.kafka_client import start_consumer, stop_consumer
from shared.observability import get_logger

# orchestrator 基地址（config.py 未提供 agent_orchestrator_base_url）
ORCHESTRATOR_URL = "http://localhost:8005"

logger = get_logger("agent-execution.kafka")

# 模块级共享 AsyncClient（懒初始化，连接池复用）
_client: httpx.AsyncClient | None = None
_consumer_task: asyncio.Task | None = None


def _get_client() -> httpx.AsyncClient:
    """获取共享 AsyncClient 实例（懒初始化，避免 import 时即创建连接）。"""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def start() -> asyncio.Task | None:
    """启动 Kafka device.anomaly 消费者后台任务。

    Kafka 未启用或启动失败时返回 None（降级，不抛异常）。
    """
    global _consumer_task
    if not settings.kafka_enabled:
        logger.info("kafka.disabled.skip_consumer")
        return None
    task = await start_consumer(
        settings.kafka_topic_device_anomaly,
        settings.kafka_consumer_group,
        _handle_device_anomaly,
    )
    if task is None:
        logger.warning("kafka.consumer.start.failed_or_disabled")
    _consumer_task = task
    return task


async def _handle_device_anomaly(message: dict) -> None:
    """处理 device.anomaly 消息：调用 orchestrator → 生成执行指令。

    任何异常都不向上抛（kafka_client 已兜底 handler 异常），失败时记录
    异常记录到 exception_records，保证消费循环不中断。

    消息格式：{"device_id": int, "symptom": str}
    """
    try:
        device_id = message.get("device_id")
        symptom = message.get("symptom", "")
        client = _get_client()
        resp = await client.post(
            f"{ORCHESTRATOR_URL}/v1/orchestrator/device_fault",
            json={"device_id": device_id, "symptom": symptom},
        )
        resp.raise_for_status()
        workflow = resp.json()
        workflow_id = workflow.get("workflow_id")
        diagnosis = workflow.get("diagnosis")
        schedule_adjustment = workflow.get("schedule_adjustment")

        # 延迟导入避免循环依赖（instruction_service 间接引用本模块的字段）
        from .models import InstructionCreateRequest
        from . import instruction_service

        req = InstructionCreateRequest(
            source_workflow_id=workflow_id,
            diagnosis=diagnosis,
            schedule_adjustment=schedule_adjustment,
        )
        await instruction_service.create_instructions(req)
        logger.info(
            "kafka.device_anomaly.handled",
            workflow_id=workflow_id,
            device_id=device_id,
        )
    except Exception as exc:
        logger.warning(
            "kafka.device_anomaly.handle_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        # 失败兜底：写入异常记录，便于后续排查
        try:
            from .models import ExceptionCreateRequest
            from . import exception_service

            await exception_service.create_exception(
                ExceptionCreateRequest(
                    source="kafka_event",
                    description=(
                        f"Kafka device.anomaly 处理失败: {exc}"
                    ),
                )
            )
        except Exception as inner:
            logger.error(
                "kafka.device_anomaly.fallback_exception_record_failed",
                error=str(inner),
            )


async def aclose() -> None:
    """关闭消费者后台任务与共享 httpx 客户端（供 lifespan shutdown 调用）。

    幂等：任务或客户端不存在时直接返回。
    """
    global _client, _consumer_task
    await stop_consumer(_consumer_task)
    _consumer_task = None
    if _client is not None:
        await _client.aclose()
        _client = None
