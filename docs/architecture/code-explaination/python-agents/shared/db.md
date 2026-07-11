# db

> PostgreSQL 连接池与工作流持久化公共模块，提供 asyncpg 连接池的线程安全懒初始化。

**模块路径**: `shared/db.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/db.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `_pool` | `asyncpg.Pool \| None` | 共享连接池单例 |
| `_pool_lock` | `async.Lock` | 连接池初始化锁 |

---

## 顶层函数

### `async get_pg_pool() -> asyncpg.Pool`

> 获取共享 asyncpg 连接池

**签名**: `async def get_pg_pool() -> asyncpg.Pool`

**返回值**: `asyncpg.Pool` — 连接池实例

**逻辑**: 双重检查 + asyncio.Lock 懒初始化

---

### `async init_workflow_table() -> None`

> 幂等创建 workflows 表与索引

**签名**: `async def init_workflow_table() -> None`

**逻辑**: 使用 `CREATE TABLE IF NOT EXISTS` 创建 workflows 表

---

### `async save_workflow(workflow_id: str, status: str, data: dict) -> None`

> UPSERT 工作流记录

**签名**: `async def save_workflow(workflow_id: str, status: str, data: dict) -> None`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `workflow_id` | `str` | 是 | 工作流 ID |
| `status` | `str` | 是 | 状态（SUCCESS/PARTIAL/FAILED） |
| `data` | `dict` | 是 | 工作流数据 |

---

### `async get_workflow(workflow_id: str) -> dict | None`

> 查询工作流记录

**签名**: `async def get_workflow(workflow_id: str) -> dict | None`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `workflow_id` | `str` | 工作流 ID |

**返回值**: `dict | None` — 工作流数据，不存在返回 None

---

### `async close_pool() -> None`

> 关闭共享连接池

**签名**: `async def close_pool() -> None`

---

### `async init_execution_tables() -> None`

> 幂等创建 Phase 4 执行闭环三张表

**签名**: `async def init_execution_tables() -> None`

**逻辑**: 创建 execution_instructions、exception_records、approvals 三张表

---

### `async create_instruction(...) -> dict`

> 插入执行指令记录

**签名**: `async def create_instruction(instruction_id: str, source_workflow_id: str | None, type: str, payload: dict, status: str = "PENDING", priority: str = "MEDIUM", auto_execute: bool = False) -> dict`

---

### `async get_instruction(instruction_id: str) -> dict | None`

> 按 instruction_id 查询指令

---

### `async list_instructions(page: int = 1, size: int = 20, status: str | None = None, type: str | None = None) -> dict`

> 分页查询指令记录

---

### `async update_instruction_status(instruction_id: str, status: str, note: str | None = None) -> dict | None`

> 更新指令状态

---

### `async create_exception(exception_id: str, source: str, instruction_id: str | None, description: str) -> dict`

> 插入异常记录

---

### `async get_exception(exception_id: str) -> dict | None`

> 按 exception_id 查询异常

---

### `async list_exceptions(page: int = 1, size: int = 20, status: str | None = None) -> dict`

> 分页查询异常记录

---

### `async update_exception_status(exception_id: str, status: str, analysis: dict | None = None) -> dict | None`

> 更新异常状态

---

### `async create_approval(instruction_id: str, decision: str, approver: str | None, comment: str | None) -> dict`

> 插入审批记录

---

### `async get_approvals_by_instruction(instruction_id: str) -> list[dict]`

> 查询某指令的全部审批记录
