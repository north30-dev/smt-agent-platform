"""Java device-service HTTP 客户端封装（共享版）。

封装设备信息查询、采集点列表、采集点历史数据查询、设备列表查询接口。
错误统一抛出 DeviceServiceUnavailable，由各 Agent 的 main.py 异常处理器兜底。

C4：从 agent-maintenance / agent-quality / agent-scheduler 三处副本合并而来。
- 全接口 async，使用 httpx.AsyncClient 避免阻塞事件循环。
- 引入 tenacity 重试（仅对 ConnectError/TimeoutException 重试）。
- 重试耗尽后 ConnectError/TimeoutException 转换为 DeviceServiceUnavailable，
  避免裸 httpx 异常泄露到上层（main.py 只处理 DeviceServiceUnavailable）。
- 模块级单例 + reset_device_client() 便于测试 mock。
"""

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.config import settings


class DeviceServiceUnavailable(Exception):
    """Java device-service 不可达或返回非 2xx。"""


class DeviceClient:
    """device-service 异步 HTTP 客户端。"""

    def __init__(
        self,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        """初始化客户端。

        Args:
            base_url: device-service 基地址，默认从 settings.device_service_base_url 取。
            client: 可选的 httpx.AsyncClient 实例（依赖注入，便于测试 mock）。
        """
        self._base_url = (base_url or settings.device_service_base_url).rstrip("/")
        self._client = client
        self._owns_client = client is None

    def _get_http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端（懒初始化，避免 import 时即创建连接）。"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def _request(
        self, path: str, params: dict | None = None
    ) -> dict | list | None:
        """统一请求与响应解析（含重试）。

        重试仅对 ConnectError/TimeoutException 生效，重试耗尽后转换为
        DeviceServiceUnavailable，确保上层只需处理单一异常类型。

        Returns:
            device-service 返回的 data 字段。

        Raises:
            DeviceServiceUnavailable: 网络错误、HTTP 非 2xx 或响应非 JSON。
        """
        url = f"{self._base_url}{path}"
        http_client = self._get_http_client()
        resp: httpx.Response | None = None

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(settings.device_service_max_retries + 1),
                wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
                retry=retry_if_exception_type(
                    (httpx.ConnectError, httpx.TimeoutException)
                ),
                reraise=True,
            ):
                with attempt:
                    try:
                        resp = await http_client.get(url, params=params)
                        resp.raise_for_status()
                    except (httpx.ConnectError, httpx.TimeoutException):
                        raise
                    except httpx.HTTPStatusError as exc:
                        raise DeviceServiceUnavailable(str(exc)) from exc
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise DeviceServiceUnavailable(
                f"device-service 不可达：{exc}"
            ) from exc

        if resp is None:
            raise DeviceServiceUnavailable("device-service 请求失败：无响应")

        try:
            data = resp.json()
        except ValueError as exc:
            raise DeviceServiceUnavailable(
                f"device-service 响应非 JSON：{exc}"
            ) from exc

        if data.get("code") != 200:
            raise DeviceServiceUnavailable(
                f"device-service 业务错误: {data.get('message')}"
            )
        return data.get("data")

    async def get_device(self, device_id: int) -> dict:
        """GET /api/device/{id}，返回设备详情。

        Raises:
            DeviceServiceUnavailable: device-service 返回空数据。
        """
        data = await self._request(f"/api/device/{device_id}")
        if data is None:
            raise DeviceServiceUnavailable(
                f"device-service 返回空数据：device_id={device_id}"
            )
        return data

    async def get_device_data(
        self,
        device_id: int,
        datapoint_code: str,
        start_time: str,
        end_time: str,
        size: int = 1000,
    ) -> list[dict]:
        """GET /api/device/{id}/data?...，返回 records 列表。"""
        data = await self._request(
            f"/api/device/{device_id}/data",
            params={
                "datapointCode": datapoint_code,
                "startTime": start_time,
                "endTime": end_time,
                "page": 1,
                "size": size,
            },
        )
        if data is None:
            return []
        records = data.get("records")
        return records or []

    async def list_datapoints(self, device_id: int) -> list[dict]:
        """GET /api/device/{id}/datapoints，返回采集点列表。"""
        data = await self._request(f"/api/device/{device_id}/datapoints")
        if data is None:
            return []
        return data

    async def list_devices(self, status: str | None = None) -> list[dict]:
        """GET /api/device/list，返回设备列表。

        Args:
            status: 可选状态过滤（如 "RUNNING"）。

        Returns:
            data.records 列表，每条记录含 id/deviceCode/deviceName/deviceType/
            productionLine/status/healthScore 字段。
        """
        params: dict = {"page": 1, "size": 200}
        if status:
            params["status"] = status
        data = await self._request("/api/device/list", params=params)
        if data is None:
            return []
        records = data.get("records")
        return records or []


# 模块级单例（AsyncClient 懒初始化，import 时不创建连接）
device_client = DeviceClient()


def get_device_client() -> DeviceClient:
    """获取 DeviceClient 单例（向后兼容入口）。"""
    return device_client


def reset_device_client() -> None:
    """重置单例的内部 HTTP 客户端（仅供测试使用）。"""
    global device_client
    if device_client._owns_client:
        device_client._client = None


async def aclose() -> None:
    """关闭单例的内部 HTTP 客户端（供 FastAPI lifespan shutdown 调用）。

    幂等：客户端未创建或已关闭时直接返回。
    """
    if device_client._client is not None:
        await device_client._client.aclose()
        device_client._client = None
