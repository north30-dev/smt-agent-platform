"""Java device-service HTTP 客户端封装。

封装设备信息查询、采集点列表、采集点历史数据查询三类接口。
错误统一抛出 DeviceServiceUnavailable，由 main.py 异常处理器兜底。
"""

import httpx

from shared.config import settings


class DeviceServiceUnavailable(Exception):
    """Java device-service 不可达或返回非 2xx。"""


class DeviceClient:
    """device-service 同步 HTTP 客户端。"""

    def __init__(self, base_url: str | None = None):
        """初始化客户端。

        Args:
            base_url: device-service 基地址，默认从 settings.device_service_base_url 取。
        """
        self._base_url = (base_url or settings.device_service_base_url).rstrip("/")
        self._client = httpx.Client(timeout=10.0)

    def _request(self, path: str, params: dict | None = None) -> dict:
        """统一请求与响应解析。

        Returns:
            device-service 返回的 data 字段（get_device_data 返回 records 列表上层结构）。
        """
        url = f"{self._base_url}{path}"
        try:
            resp = self._client.get(url, params=params)
            resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            raise DeviceServiceUnavailable(str(exc)) from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise DeviceServiceUnavailable(f"device-service 响应非 JSON：{exc}") from exc

        if data.get("code") != 200:
            raise DeviceServiceUnavailable(
                f"device-service 业务错误: {data.get('message')}"
            )
        return data["data"]

    def get_device(self, device_id: int) -> dict:
        """GET /api/device/{id}，返回设备信息。"""
        return self._request(f"/api/device/{device_id}")

    def get_device_data(
        self,
        device_id: int,
        datapoint_code: str,
        start_time: str,
        end_time: str,
        size: int = 1000,
    ) -> list[dict]:
        """GET /api/device/{id}/data?...，返回 records 列表。"""
        data = self._request(
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

    def list_datapoints(self, device_id: int) -> list[dict]:
        """GET /api/device/{id}/datapoints，返回采集点列表。"""
        data = self._request(f"/api/device/{device_id}/datapoints")
        if data is None:
            return []
        return data


# 模块级单例
device_client = DeviceClient()
