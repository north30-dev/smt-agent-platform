"""子 Agent HTTP 客户端封装。

封装 maintenance / quality / scheduler 三个子 Agent 的 HTTP 调用。
- 使用 httpx.AsyncClient 避免阻塞事件循环。
- 引入 tenacity 重试（对 ConnectError/TimeoutException/ServiceBusy）。
- 网络错误统一抛出 AgentUnavailable，由 nodes 层捕获并降级为 skipped 状态。

参考 agent-maintenance/device_client.py 的实现模式。
"""

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from shared.config import settings


class ServiceBusy(Exception):
    """子 Agent 返回 502/503/504 — 暂时繁忙（如正在处理 LLM 长耗时请求），可重试。"""


class AgentUnavailable(Exception):
    """子 Agent 不可达或返回非 2xx。

    Attributes:
        agent_name: 出错的 Agent 名称（maintenance/quality/scheduler）。
    """

    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        super().__init__(message)


class AgentClients:
    """三个子 Agent 的异步 HTTP 客户端集合。"""

    def __init__(
        self,
        maintenance_url: str,
        quality_url: str,
        scheduler_url: str,
        client: httpx.AsyncClient | None = None,
    ):
        """初始化客户端。

        Args:
            maintenance_url: maintenance Agent 基地址。
            quality_url: quality Agent 基地址。
            scheduler_url: scheduler Agent 基地址。
            client: 可选的共享 httpx.AsyncClient（依赖注入，便于测试 mock）。
        """
        self._maintenance_url = maintenance_url.rstrip("/")
        self._quality_url = quality_url.rstrip("/")
        self._scheduler_url = scheduler_url.rstrip("/")
        self._client = client
        self._owns_client = client is None

    def _get_http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端（懒初始化，避免 import 时即创建连接）。"""
        if self._client is None:
            # 60s 超时：子 Agent 的 LLM 调用（如根因分析）可能耗时 20-30s
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def _post(self, agent_name: str, url: str, payload: dict) -> dict:
        """统一 POST 请求与响应解析（含 tenacity 重试）。

        Args:
            agent_name: Agent 名称，用于 AgentUnavailable 标识。
            url: 完整请求 URL。
            payload: 请求体 JSON。

        Returns:
            Agent 返回的 JSON 响应 dict。

        Raises:
            AgentUnavailable: 网络错误或 HTTP 非 2xx 或响应非 JSON。
        """
        http_client = self._get_http_client()
        resp: httpx.Response | None = None

        # 对网络错误和 502/503/504 重试，其余 HTTP 业务错误不重试
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=0.5, max=3, jitter=0.5),
            retry=retry_if_exception_type(
                (httpx.ConnectError, httpx.TimeoutException, ServiceBusy)
            ),
            reraise=True,
        ):
            with attempt:
                try:
                    resp = await http_client.post(url, json=payload)
                    resp.raise_for_status()
                except (httpx.ConnectError, httpx.TimeoutException):
                    raise
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in (502, 503, 504):
                        raise ServiceBusy(
                            f"{agent_name} agent 繁忙 (HTTP {exc.response.status_code})"
                        ) from exc
                    raise AgentUnavailable(
                        agent_name,
                        f"{agent_name} agent 返回非 2xx: {exc.response.status_code}",
                    ) from exc

        if resp is None:
            raise AgentUnavailable(agent_name, f"{agent_name} agent 请求失败：无响应")

        try:
            return resp.json()
        except ValueError as exc:
            raise AgentUnavailable(
                agent_name, f"{agent_name} agent 响应非 JSON: {exc}"
            ) from exc

    async def call_maintenance(self, device_id: int, symptom: str) -> dict:
        """调用 maintenance diagnose 接口。

        Args:
            device_id: 设备 ID。
            symptom: 故障现象。

        Returns:
            {"root_causes": [...], "repair_suggestions": [...], "similar_cases": [...]}
        """
        url = f"{self._maintenance_url}/v1/maintenance/diagnose"
        try:
            return await self._post(
                "maintenance", url, {"device_id": device_id, "symptom": symptom}
            )
        except (httpx.ConnectError, httpx.TimeoutException, ServiceBusy) as exc:
            raise AgentUnavailable(
                "maintenance", f"maintenance agent 不可达: {exc}"
            ) from exc

    async def call_quality(self, device_id: int, defect_description: str) -> dict:
        """调用 quality root_cause 接口。

        Args:
            device_id: 设备 ID。
            defect_description: 缺陷描述（复用 symptom）。

        Returns:
            {"device_id": int, "root_causes": [...],
             "corrective_actions": [...], "similar_cases": [...]}
        """
        url = f"{self._quality_url}/v1/quality/root_cause"
        try:
            return await self._post(
                "quality",
                url,
                {"device_id": device_id, "defect_description": defect_description},
            )
        except (httpx.ConnectError, httpx.TimeoutException, ServiceBusy) as exc:
            raise AgentUnavailable(
                "quality", f"quality agent 不可达: {exc}"
            ) from exc

    async def call_scheduler(
        self,
        order_no: str,
        product_model: str,
        quantity: int,
        delivery_date: str,
        source: str = "user",
    ) -> dict:
        """调用 scheduler urgent 接口（急单插单）。

        Args:
            order_no: 急单单号。
            product_model: 产品型号。
            quantity: 数量。
            delivery_date: 交付日期（ISO 日期字符串）。
            source: 订单来源（user/orchestrator_synthetic），用于追溯合成急单。

        Returns:
            {"urgent_order_no": str, "affected_orders": [...],
             "estimated_delay_hours": float,
             "adjustment_plan": {"changeover_suggestion": str,
                                 "overtime_suggestion": str}}
        """
        url = f"{self._scheduler_url}/v1/scheduler/urgent"
        try:
            return await self._post(
                "scheduler",
                url,
                {
                    "order_no": order_no,
                    "product_model": product_model,
                    "quantity": quantity,
                    "delivery_date": delivery_date,
                    "source": source,
                },
            )
        except (httpx.ConnectError, httpx.TimeoutException, ServiceBusy) as exc:
            raise AgentUnavailable(
                "scheduler", f"scheduler agent 不可达: {exc}"
            ) from exc


# 模块级单例（AsyncClient 懒初始化，import 时不创建连接）
agent_clients = AgentClients(
    settings.agent_maintenance_base_url,
    settings.agent_quality_base_url,
    settings.agent_scheduler_base_url,
)


def reset_agent_clients() -> None:
    """重置单例的内部 HTTP 客户端（仅供测试使用）。"""
    global agent_clients
    if agent_clients._owns_client:
        agent_clients._client = None


async def aclose() -> None:
    """关闭单例的内部 HTTP 客户端（供 FastAPI lifespan shutdown 调用）。

    幂等：客户端未创建或已关闭时直接返回。
    """
    if agent_clients._client is not None:
        await agent_clients._client.aclose()
        agent_clients._client = None
