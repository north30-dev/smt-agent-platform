# agent-maintenance/diagnose

> 故障诊断模块，串联设备信息查询、相似案例检索、大模型对话。

**模块路径**: `agent-maintenance/diagnose.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/diagnose.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `COLLECTION` | `str` | `"smt_fault_cases"` |
| `_PROMPT_FILE` | `Path` | 提示词模板路径 |
| `_initialized` | `bool` | collection 是否已初始化 |
| `_init_lock` | `threading.Lock` | 初始化锁 |

---

## 顶层函数

### `async create_case(device_type: str, symptom: str, root_cause: str, solution: str) -> str`

> 录入故障案例

**签名**: `async def create_case(device_type: str, symptom: str, root_cause: str, solution: str) -> str`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device_type` | `str` | 是 | 设备类型 |
| `symptom` | `str` | 是 | 故障症状 |
| `root_cause` | `str` | 是 | 根因 |
| `solution` | `str` | 是 | 解决方案 |

**返回值**: `str` — 生成的 case_id（`case-{uuid8}`）

**逻辑**: 构建案例文本 → 嵌入向量 → 插入 Milvus

---

### `async diagnose(device_id: int, symptom: str) -> dict`

> 故障诊断

**签名**: `async def diagnose(device_id: int, symptom: str) -> dict`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device_id` | `int` | 是 | 设备 ID |
| `symptom` | `str` | 是 | 故障症状描述 |

**返回值**: `dict` — `{root_causes, repair_suggestions, similar_cases}`

**逻辑**:
1. 获取设备信息（device_client.get_device）
2. 嵌入症状 → Milvus 检索 top 3 相似案例
3. 构建提示词（设备信息 + 相似案例 + JSON 输出约束）
4. 用户输入包裹在 `<user_input>` 标签（SEC-3）
5. 调用 LLM
6. 解析输出（JSON → extract_json_block → fallback）

---

### `_parse_llm_output(raw_text: str) -> tuple[list[str], list[str]]`

> 解析 LLM 输出

**签名**: `def _parse_llm_output(raw_text: str) -> tuple[list[str], list[str]]`

**返回值**: `tuple[list[str], list[str]]` — (root_causes, repair_suggestions)

**逻辑**: 直接 JSON 解析 → extract_json_block → fallback `[raw_text], []`
