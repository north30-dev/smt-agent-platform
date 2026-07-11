# observability

> 可观测性模块，提供结构化日志配置和 /healthz 健康检查端点注册。

**模块路径**: `shared/observability.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/observability.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `_start_time` | `float` | 应用启动时间（monotonic） |
| `_VERSION` | `str` | 版本号 `"0.2.0"` |

---

## 类

### `HealthCheck(BaseModel)`

> 单个健康检查项

**字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 检查项名称 |
| `status` | `str` | 状态（ok/degraded/down） |
| `detail` | `str` | 详细信息（可选） |

---

### `HealthResponse(BaseModel)`

> /healthz 响应模型

**字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | `str` | 整体状态 |
| `uptime_seconds` | `float` | 运行时长（秒） |
| `version` | `str` | 版本号 |
| `checks` | `list[HealthCheck]` | 检查项列表 |

---

## 顶层函数

### `setup_logging(level: str = "INFO") -> structlog.BoundLogger`

> 配置 structlog 结构化日志

**签名**: `def setup_logging(level: str = "INFO") -> structlog.BoundLogger`

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `level` | `str` | `"INFO"` | 日志级别 |

**返回值**: `structlog.BoundLogger` — 配置好的 logger

**逻辑**: 配置 structlog 处理链（时间戳+级别+位置 → JSON 格式化）

---

### `get_logger(name: str = "smt") -> structlog.BoundLogger`

> 获取结构化 logger

**签名**: `def get_logger(name: str = "smt") -> structlog.BoundLogger`

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `"smt"` | Logger 名称 |

**返回值**: `structlog.BoundLogger` — 绑定名称的 logger

---

### `register_health_endpoint(app: FastAPI, name: str, checks: list[Any] | None = None) -> None`

> 注册 /healthz 健康检查端点

**签名**: `def register_health_endpoint(app: FastAPI, name: str, checks: list[Any] | None = None) -> None`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `app` | `FastAPI` | 是 | FastAPI 应用实例 |
| `name` | `str` | 是 | 服务名称 |
| `checks` | `list[Any] \| None` | 否 | 额外检查项 |

**逻辑**: 注册 `GET /healthz` 端点 → 返回 `HealthResponse`（含 uptime、version、checks）
