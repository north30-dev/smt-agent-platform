# agent-quality/root_cause

> 质量根因分析模块，基于人/机/料/法/环五因素框架 + LLM 分析。

**模块路径**: `agent-quality/root_cause.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-quality/root_cause.py`

---

## 模块级常量

| 名称 | 类型 | 说明 |
|------|------|------|
| `COLLECTION` | `str` | `"smt_quality_cases"` |
| `_PROMPT_FILE` | `Path` | 提示词模板路径 |
| `_initialized` | `bool` | collection 是否已初始化 |
| `_init_lock` | `threading.Lock` | 初始化锁 |

---

## 顶层函数

### `async create_case(defect_type: str, description: str, root_cause: str, corrective_action: str) -> str`

> 录入质量案例

**签名**: `async def create_case(...) -> str`

**返回值**: `str` — 生成的 case_id（`qcase-{uuid8}`）

---

### `async analyze(device_id: int, defect_description: str) -> dict`

> 根因分析

**签名**: `async def analyze(device_id: int, defect_description: str) -> dict`

**返回值**: `dict` — `{device_id, root_causes, corrective_actions, similar_cases}`

**逻辑**:
1. 获取设备信息
2. 嵌入缺陷描述 → Milvus 检索 top 3 相似案例
3. 构建提示词（使用 `str.replace()` 避免 JSON 花括号冲突）
4. 用户输入包裹在 `<user_input>` 标签（SEC-3）
5. 调用 LLM
6. 解析输出（root_causes 为 `{category, cause}` 列表）

---

### `_parse_llm_output(raw_text: str) -> tuple[list[dict], list[str]]`

> 解析 LLM 输出

**返回值**: `tuple[list[dict], list[str]]` — (root_causes, corrective_actions)

**root_causes 格式**: `[{"category": "人/机/料/法/环", "cause": "具体原因"}]`
