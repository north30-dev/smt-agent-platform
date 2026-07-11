# device_client

> Java device-service HTTP 客户端封装，提供设备信息查询、采集点列表、历史数据查询等接口。

**模块路径**: `shared/device_client.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/device_client.py`

---

## 模块级对象

| 名称 | 类型 | 说明 |
|------|------|------|
| `device_client` | `DeviceClient` | 全局单例 |

---

## 类

### `DeviceServiceUnavailable(Exception)`

> Java device-service 不可达或返回非 2xx

**签名**: `class DeviceServiceUnavailable(Exception)`

---

### `DeviceClient`

> device-service 异步 HTTP 客户端

**签名**: `class DeviceClient`

#### `__init__(self, base_url: str | None = None, client: httpx.AsyncClient | None = None)`

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `base_url` | `str \| None` | `None` | 服务地址（默认从 settings 读取） |
| `client` | `httpx.AsyncClient \| None` | `None` | 注入的 HTTP 客户端（测试用） |

#### 方法

##### `async get_device(self, device_id: int) -> dict`

> 获取设备详情

**签名**: `async def get_device(self, device_id: int) -> dict`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `device_id` | `int` | 设备 ID |

**返回值**: `dict` — 设备信息

**逻辑**: GET `/api/device/{device_id}`

---

##### `async get_device_data(self, device_id: int, datapoint_code: str, start_time: str, end_time: str, size: int = 1000) -> list[dict]`

> 查询设备历史数据

**签名**: `async def get_device_data(self, device_id: int, datapoint_code: str, start_time: str, end_time: str, size: int = 1000) -> list[dict]`

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `device_id` | `int` | — | 设备 ID |
| `datapoint_code` | `str` | — | 采集点编码 |
| `start_time` | `str` | — | 开始时间（ISO-8601） |
| `end_time` | `str` | — | 结束时间（ISO-8601） |
| `size` | `int` | `1000` | 返回条数 |

**返回值**: `list[dict]` — 数据记录列表（records 字段）

---

##### `async list_datapoints(self, device_id: int) -> list[dict]`

> 查询设备采集点列表

**签名**: `async def list_datapoints(self, device_id: int) -> list[dict]`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `device_id` | `int` | 设备 ID |

**返回值**: `list[dict]` — 采集点列表

---

##### `async list_devices(self, status: str | None = None) -> list[dict]`

> 查询设备列表

**签名**: `async def list_devices(self, status: str | None = None) -> list[dict]`

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status` | `str \| None` | `None` | 状态筛选 |

**返回值**: `list[dict]` — 设备列表（records 字段）

---

## 顶层函数

### `get_device_client() -> DeviceClient`

> 获取 DeviceClient 单例

### `reset_device_client() -> None`

> 重置单例（仅供测试）

### `async aclose() -> None`

> 关闭单例的 HTTP 客户端
