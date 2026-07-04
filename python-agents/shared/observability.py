"""可观测性模块（logging + healthz）。

PRD §5 非功能需求：可维护性 — 提供完整 APM 监控、日志链路追踪。
提供结构化日志配置、/healthz 健康检查端点注册。
"""

import logging
import sys
import time
from typing import Any

import structlog
from fastapi import FastAPI
from pydantic import BaseModel


class HealthCheck(BaseModel):
    """单个健康检查项。"""

    name: str
    status: str  # "pass" | "fail" | "warn"
    detail: str = ""


class HealthResponse(BaseModel):
    """/healthz 响应模型。"""

    status: str  # "healthy" | "unhealthy"
    uptime_seconds: float
    version: str
    checks: list[HealthCheck]


_start_time: float = time.monotonic()

_VERSION = "0.2.0"


def setup_logging(level: str = "INFO") -> structlog.BoundLogger:
    """配置 structlog 结构化日志。

    Args:
        level: 日志级别字符串（DEBUG/INFO/WARNING/ERROR）。

    Returns:
        配置好的 BoundLogger 实例。
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


def get_logger(name: str = "smt") -> structlog.BoundLogger:
    """获取结构化 logger。"""
    return structlog.get_logger(name)


def register_health_endpoint(
    app: FastAPI,
    name: str,
    checks: list[Any] | None = None,
) -> None:
    """注册 /healthz 健康检查端点。

    Args:
        app: FastAPI 应用实例。
        name: Agent 名称（如 "knowledge" / "maintenance"）。
        checks: 可选的健康检查函数列表，每个函数返回 HealthCheck。
    """
    check_funcs = checks or []

    @app.get("/healthz", tags=["observability"])
    async def healthz() -> HealthResponse:
        check_results: list[HealthCheck] = []
        overall_healthy = True

        for check_func in check_funcs:
            try:
                result = check_func()
                if isinstance(result, HealthCheck):
                    check_results.append(result)
                    if result.status == "fail":
                        overall_healthy = False
            except Exception as exc:
                check_results.append(
                    HealthCheck(
                        name=getattr(check_func, "__name__", "unknown"),
                        status="fail",
                        detail=str(exc),
                    )
                )
                overall_healthy = False

        return HealthResponse(
            status="healthy" if overall_healthy else "unhealthy",
            uptime_seconds=round(time.monotonic() - _start_time, 2),
            version=_VERSION,
            checks=check_results,
        )
