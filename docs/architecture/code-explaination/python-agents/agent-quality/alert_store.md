# agent-quality/alert_store

> 质量告警记录 PostgreSQL 存储。

**模块路径**: `agent-quality/alert_store.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-quality/alert_store.py`

---

## 顶层函数

### `async save_alert(device_id: int, defect_rate: float, threshold: float, status: str, datapoint_code: str | None) -> int`

> 保存告警记录

**签名**: `async def save_alert(...) -> int`

**返回值**: `int` — 自动生成的告警 ID

---

### `async list_alerts(page: int = 1, size: int | None = None) -> dict`

> 分页查询告警记录

**签名**: `async def list_alerts(page: int = 1, size: int | None = None) -> dict`

**返回值**: `dict` — `{records, total, page, size}`

**排序**: 按 `alert_time DESC`

---

### `async close_pool() -> None`

> 关闭连接池（仅供测试）
