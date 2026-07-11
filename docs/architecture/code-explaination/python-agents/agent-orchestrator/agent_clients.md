# agent-orchestrator/agent_clients

> 子 Agent HTTP 客户端封装，封装 maintenance / quality / scheduler / execution 四个子 Agent 的调用。

**模块路径**: `agent-orchestrator/agent_clients.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-orchestrator/agent_clients.py`

---

## 模块级对象

| 名称 | 类型 | 说明 |
|------|------|------|
| `agent_clients` | `AgentClients` | 全局单例 |

---

## 类

### `ServiceBusy(Exception)`

> 子 Agent 返回 502/503/504

---

### `AgentUnavailable(Exception)`

> 子 Agent 不可达

**属性**: `agent_name: str`

---

### `AgentClients`

> 子 Agent HTTP 客户端

#### `__init__(self, maintenance_url, quality_url, scheduler_url, execution_url, client=None)`

#### 方法

##### `async call_maintenance(self, device_id: int, symptom: str) -> dict`

> 调用运维诊断

**逻辑**: POST `/v1/maintenance/diagnose` → `{device_id, symptom}`

---

##### `async call_quality(self, device_id: int, defect_description: str) -> dict`

> 调用质量分析

**逻辑**: POST `/v1/quality/root_cause` → `{device_id, defect_description}`

---

##### `async call_scheduler(self, order_no, product_model, quantity, delivery_date, source="user") -> dict`

> 调用调度急单

**逻辑**: POST `/v1/scheduler/urgent` → `{order_no, product_model, quantity, delivery_date, source}`

---

##### `async call_execution(self, source_workflow_id, diagnosis, schedule_adjustment) -> list[dict]`

> 调用执行指令

**逻辑**: POST `/v1/execution/instructions` → `{source_workflow_id, diagnosis, schedule_adjustment}`

---

##### `async _post(self, agent_name, url, payload) -> dict`

> 统一 POST 请求（含 tenacity 重试）

**重试策略**: 3 次，指数退避，重试 ConnectError/TimeoutException/ServiceBusy
