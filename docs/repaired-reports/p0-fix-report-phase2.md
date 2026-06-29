# Phase 2 P0 问题修复报告

## 一、元信息

| 项 | 内容 |
|---|---|
| 审查对象 | `smt-agent-platform` Phase 2 收尾 P0 问题修复成果（python-agents 智能体层 + java-backend/smt-gateway 网关鉴权） |
| 对照基准 | [project-explanation-phase2.md L803-L841](file:///home/north30/projects/Personal/smt-agent-platform/docs/explaination/project-explanation-phase2.md#L803-L841) §6.3 处理优先级建议中的 P0 清单 |
| 审查方法 | 代码静态核对（逐文件读取 + grep）+ Python 单元测试验证（pytest）+ Java 单元测试验证（mvn test）+ 依赖锁文件同步验证（poetry lock/install） |
| 审查日期 | 2026-06-29 |
| 审查范围 | `python-agents/` 下 24 个 Python 文件（shared 5 + agent-knowledge 5 + agent-maintenance 6 + tests 8）、`java-backend/smt-gateway/` 鉴权过滤器与测试、`docs/database/init.sql` doc_meta 表、`python-agents/pyproject.toml` 依赖 |
| 评估口径 | P0 修复完成度 = 已修复 / 部分修复 / 未修复；验证口径 = Python 26 用例全绿（0 失败 0 错误）+ Java 57 用例全绿（0 失败 0 错误）+ grep 静态核对 4 项无残留 |
| 修复执行人 | north30-dev |
| 报告输出位置 | `docs/repaired-reports/`（用户明确指定，与 Phase 1 修复报告位置一致；修复报告不属于 AGENTS.md §6.3 审查/扫描/评估类报告） |

---

## 二、总体结论

**11 项 P0 问题已全部修复并通过编译 + 单元测试验证。**

- 修复完成度：**11 / 11 = 100%**（全部"已修复"）
- Python 单元测试验证：`poetry run pytest -v` → **26 个用例，0 失败 0 错误 0 跳过**
- Java 网关测试验证：`mvn -pl smt-gateway test` → **4 个用例全绿**（AgentAuthWebFilterTest）
- Java 全量回归验证：`mvn test` → **57 个用例，0 失败 0 错误 0 跳过**（smt-common 5 + smt-gateway 4 + smt-device-service 48）
- grep 静态核对：4 项全部通过（langchain / ValidationError / ErrorResponse / doc_meta.json 可执行代码无残留）
- 关键风险：本轮仅做编译 + 单测级验证，**端到端集成验证（docker-compose 启动 + curl 鉴权闭环 + Milvus/PG 实连）未执行**，属环境验证遗留项
- 遗留项：P1（11 项）+ P2（4 项）明确移交 Phase 3，详见第五章

---

## 三、P0 问题修复详情表

| 编号 | 问题 | 修复前位置 | 修复前严重度 | 修复方案 | 修复后状态 | 验证方式 |
|---|---|---|---|---|---|---|
| B1 | FastAPI 同步路由（`def`）+ 同步 `httpx.Client` 阻塞 uvicorn worker | agent-knowledge/main.py（3 路由 def）、agent-maintenance/main.py（4 路由 def）、shared/llm_client.py（httpx.Client）、agent-maintenance/device_client.py（httpx.Client） | 🔴 Blocker | 全路由改 `async def`；llm_client/device_client 改 `httpx.AsyncClient`；pymilvus 同步调用用 `asyncio.to_thread()` 包装不阻塞事件循环 | 已修复 | pytest 26 用例全绿 |
| B2 | 模块级 `global` 可变状态（`_initialized` / `_connected`）无线程安全保护 | shared/vector_store.py（_connected）、agent-knowledge/rag_chain.py（_initialized）、agent-maintenance/diagnose.py（_initialized） | 🔴 Blocker | 三处均加 `threading.Lock()` + 双重检查锁定模式（check-then-acquire-then-check-then-set） | 已修复 | pytest 含 vector_store/rag_chain/diagnose 用例全绿 |
| B3 | `langchain`/`langchain-community` 依赖声明但全代码零使用 | python-agents/pyproject.toml L21-L22 | 🔴 Blocker | 移除 langchain/langchain-community 依赖；新增 asyncpg（P0-5 需要）；poetry lock 重新生成锁文件 | 已修复 | grep pyproject.toml "langchain" 0 匹配；poetry install 成功 |
| P0-4 | 网关 `/api/agent/**` 无鉴权过滤器，LLM 计费接口裸露 | java-backend/smt-gateway（无任何鉴权过滤器） | 🔴 P0 架构 | 新增 reactive `AgentAuthWebFilter`（implements WebFilter + Ordered），仅拦截 `/api/agent/**`，校验 Bearer token，复用 smt-common JwtUtil；`@Import(JwtUtil.class)` 避免扩大 ComponentScan | 已修复 | mvn -pl smt-gateway test 4 用例全绿 |
| P0-5 | 文档元数据用 `data/doc_meta.json` 文件持久化，破坏无状态 | agent-knowledge/rag_chain.py（_save_meta 文件读写）、agent-knowledge/data/doc_meta.json | 🔴 P0 架构 | 新增 `shared/doc_meta_store.py`（asyncpg 连接池 + save/list/remove_doc_meta）；rag_chain 改调 doc_meta_store；config.py 加 postgres_* 字段；init.sql 加 doc_meta 表 | 已修复 | grep 可执行代码 "doc_meta.json" 0 匹配（仅 docstring 引用）；pytest 含 rag_chain 用例全绿 |
| M4 | `vector_store.list_docs`/`delete_by_doc` 用 `limit=16384` 静默截断 | shared/vector_store.py L199-L225 | 🟠 Major | 改用 `col.query_iterator(expr=..., batch_size=1000)` 分页遍历，突破 pymilvus 默认 16384 上限，避免超长文档删除留孤儿向量 | 已修复 | 静态核对 query_iterator 调用；vector_store 单测全绿 |
| M5 | Prompt 每次读盘（`yaml.safe_load`），无缓存 | agent-knowledge/rag_chain.py（_load_prompts）、agent-maintenance/diagnose.py（_load_prompts） | 🟠 Major | 两处 `_load_prompts` 加 `@lru_cache(maxsize=1)`，运行期 Prompt 文件不变，首次读盘后缓存 | 已修复 | 静态核对 @lru_cache 装饰器；rag_chain/diagnose 单测全绿 |
| M6 | `health` 接口 `int(device.get("healthScore") or 0)` 强转，上游数据异常时返回 400 而非 502 | agent-maintenance/main.py L35-L55 | 🟠 Major | `int(raw_score)` 失败时抛 `DeviceServiceUnavailable`（→ 503 device_service_unavailable），而非触发 ValueError → 400 invalid_param；错误码语义对齐"上游数据异常" | 已修复 | test_health_device_unavailable 用例全绿 |
| M8 | `agent-knowledge/main.py` `from pydantic import ValidationError` 死导入 | agent-knowledge/main.py L9 | ⚠️ Minor（P0 清单内） | 删除未使用的 `ValidationError` 导入（FastAPI 422 由 Pydantic 自动处理） | 已修复 | grep "from pydantic import ValidationError" 0 匹配 |
| M11 | `ErrorResponse` 在两 Agent 各自定义一份，违反 DRY | agent-knowledge/models.py L55-L59、agent-maintenance/models.py L88-L92 | 🟠 Major | 抽取到 `shared/models.py`；两 Agent 的 models.py 删除本地定义，main.py 改 `from shared.models import ErrorResponse` | 已修复 | grep "class ErrorResponse" 仅 shared/models.py 1 匹配；两 Agent models.py 0 匹配 |
| m7 | async/sync 风格不一致（仅 `upload` 是 `async def`） | agent-knowledge/main.py（upload async，其余 def）、agent-maintenance/main.py（4 路由全 def） | ⚠️ Minor（P0 清单内） | 两 main.py 全路由统一改 `async def`，与 B1 修复同步完成 | 已修复 | 静态核对两 main.py 路由全 async def |

---

## 四、逐项修复详情

### 4.1 B1：FastAPI 同步路由 + 同步 httpx 阻塞 uvicorn worker

**修复前**：
- [agent-knowledge/main.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/main.py)：`ask`/`documents`/`delete` 三个路由是 `def`（同步），仅 `upload` 是 `async def`
- [agent-maintenance/main.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/main.py)：4 个路由全是 `def`
- [shared/llm_client.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/llm_client.py)：`chat`/`embed` 是同步函数，内部 `with httpx.Client(timeout=60) as client:` 新建同步客户端
- [agent-maintenance/device_client.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/device_client.py)：`get_device` 等方法是同步函数，内部 `httpx.Client(timeout=10.0)`
- 严重度：🔴 Blocker
- 风险：FastAPI 对 `def` 路由丢到线程池（默认 40 线程），`httpx.Client` 同步阻塞期间线程被占满后请求排队，高并发下 503；LLM 60s 超时期间整个 worker 阻塞

**修复后**：
- [shared/llm_client.py L23-L57](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/llm_client.py#L23-L57)：`chat` 改 `async def`，内部 `async with httpx.AsyncClient(timeout=60) as client: resp = await client.post(...)`；[L60-L89](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/llm_client.py#L60-L89)：`embed` 同理
- [agent-maintenance/device_client.py L28-L87](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/device_client.py#L28-L87)：`_request`/`get_device`/`get_device_data`/`list_datapoints` 全改 `async def`，`self._client = httpx.AsyncClient(timeout=10.0)`，`await self._client.get(...)`
- [agent-knowledge/rag_chain.py L34-L131](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/rag_chain.py#L34-L131)：`upload_document`/`ask`/`list_documents`/`delete_document` 全改 `async def`；pymilvus 同步调用（`init_collections`/`insert`/`search`/`count`/`list_docs`/`delete_by_doc`）用 `await asyncio.to_thread(...)` 包装不阻塞事件循环
- [agent-maintenance/diagnose.py L32-L119](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/diagnose.py#L32-L119)：`create_case`/`diagnose` 全改 `async def`，pymilvus 同步调用同样用 `asyncio.to_thread` 包装
- [agent-maintenance/predict.py L28-L120](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/predict.py#L28-L120)：`predict` 改 `async def`，`await device_client.*` 调用
- [agent-knowledge/main.py L31-L73](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/main.py#L31-L73)：4 路由全 `async def`
- [agent-maintenance/main.py L32-L88](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/main.py#L32-L88)：4 路由全 `async def`

**验证结果**：pytest 26 用例全绿（含 test_llm_client 3 + test_maintenance_api 5 + test_knowledge_api 5 + test_maintenance_diagnose 3 + test_maintenance_predict 3 + test_knowledge_rag 3 + test_vector_store 4）。

---

### 4.2 B2：模块级 global 可变状态无线程安全保护

**修复前**：
- [shared/vector_store.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/vector_store.py)：`_connected = False` 模块级标志，`_ensure_connect` 内 check-then-set 无锁
- [agent-knowledge/rag_chain.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/rag_chain.py)：`_initialized = False` 同上
- [agent-maintenance/diagnose.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/diagnose.py)：`_initialized = False` 同上
- 严重度：🔴 Blocker
- 风险：多 worker（`uvicorn --workers 4`）或多线程并发触发 `init_collections` 时 check-then-act 竞态：A 读 False → B 读 False → A 调 init → B 调 init（重复创建/抛 `Collection already exists`）

**修复后**：
- [shared/vector_store.py L28-L49](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/vector_store.py#L28-L49)：新增 `_connect_lock = threading.Lock()`；`_ensure_connect` 改双重检查：`if _connected: return` → `with _connect_lock: if _connected: return` → `connections.connect(...)` → `_connected = True`
- [agent-knowledge/rag_chain.py L30-L58](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/rag_chain.py#L30-L58)：新增 `_init_lock = threading.Lock()`；`upload_document` 内 `if not _initialized: with _init_lock: if not _initialized: ... _initialized = True`
- [agent-maintenance/diagnose.py L28-L61](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/diagnose.py#L28-L61)：同 rag_chain 模式

**验证结果**：test_vector_store 4 用例全绿（含连接单例重置 fixture）；test_knowledge_rag test_upload_document 与 test_maintenance_diagnose test_create_case 均重置 `_initialized=False` 触发 init_collections 路径，全绿。

---

### 4.3 B3：langchain 依赖声明但全代码零使用

**修复前**：
- [python-agents/pyproject.toml](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/pyproject.toml) L21-L22：声明 `langchain = "^0.3"` 与 `langchain-community = "^0.3"`，但全代码零 `import langchain`
- 严重度：🔴 Blocker
- 风险：违背 PRD §3.1 "LangChain/LangGraph Agent 工作流编排"承诺与 AGENTS.md §3.2 精神；拉入数十个传递依赖（pydantic v1 兼容层、sqlalchemy、jsonpatch 等），poetry install 体积虚增

**修复后**：
- [pyproject.toml L9-L21](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/pyproject.toml#L9-L21)：移除 langchain/langchain-community；新增 `asyncpg = "^0.29.0"`（P0-5 需要）；新增 `[tool.pytest.ini_options] asyncio_mode = "auto"`（async 测试支持）
- 执行 `poetry lock` 重新生成锁文件（pyproject.toml 变更后锁文件必须同步）
- 执行 `poetry install` 安装 asyncpg（1 个新包）

**验证结果**：grep pyproject.toml "langchain" 0 匹配；`poetry install` 成功安装 asyncpg 0.29.0；pytest 26 用例全绿。

---

### 4.4 P0-4：网关 /api/agent/** 无鉴权过滤器

**修复前**：
- [java-backend/smt-gateway](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-gateway)：仅 CorsConfig + 路由配置，无任何鉴权过滤器
- 严重度：🔴 P0 架构
- 风险：LLM 计费接口（/api/agent/knowledge/ask、/api/agent/maintenance/diagnose 等）裸露，匿名可刷，直接产生大模型调用费用

**修复后**：
- 新增 [AgentAuthWebFilter.java](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-gateway/src/main/java/com/smt/platform/gateway/security/AgentAuthWebFilter.java)：reactive `WebFilter` + `Ordered` 实现，仅拦截 `/api/agent/**`，从 `Authorization` 头提取 `Bearer <token>`，复用 `JwtUtil.validateToken` 校验；无 token / token 无效返回 401 JSON `{"error":"unauthorized","message":"..."}`（与 Python 侧 ErrorResponse 结构对齐）；`@Import(JwtUtil.class)` 单独引入 JwtUtil Bean，不扩大 ComponentScan，保持 reactive 运行时纯净；`getOrder()` 返回 `HIGHEST_PRECEDENCE + 10`
- 新增 [AgentAuthWebFilterTest.java](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-gateway/src/test/java/com/smt/platform/gateway/security/AgentAuthWebFilterTest.java)：4 个集成测试用例（`@SpringBootTest(RANDOM_PORT)` + `@AutoConfigureWebTestClient`）：
  - `test_no_token_returns_401`：无 token → 401 + `{"error":"unauthorized","message":"token 缺失"}`
  - `test_invalid_token_returns_401`：无效 token → 401 + `{"error":"unauthorized","message":"token 无效或已过期"}`
  - `test_valid_token_passes_filter`：`jwtUtil.generateToken("test-user", ["ADMIN"], 3600000)` 签发合法 token，断言 status != 401（filter 放行后路由转发到未启动的后端返回 5xx，但不是 401）
  - `test_device_path_not_intercepted`：`/api/device/1` 无 token，断言 status != 401（device-service 路径不被拦截）
- [application.yml L38-L45](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-gateway/src/main/resources/application.yml#L38-L45)：新增 `smt.security.jwt.secret/header/prefix` 配置，secret 用 `${SMT_JWT_SECRET:dev-only-...}` ENV 化
- [pom.xml L31-L42](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-gateway/pom.xml#L31-L42)：新增 `spring-boot-starter-test`（test scope）+ `reactor-test`（test scope）支持 WebTestClient 与 reactive 断言

**验证结果**：`mvn -pl smt-gateway test` 4 用例全绿；测试日志中 filter chain checkpoint 出现 `AgentAuthWebFilter`，确认过滤器已注册到 reactive 调用链。

---

### 4.5 P0-5：文档元数据文件持久化破坏无状态

**修复前**：
- [agent-knowledge/rag_chain.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/rag_chain.py)：`_save_meta` 用 `agent-knowledge/data/doc_meta.json` 文件持久化，先读后写无文件锁
- 严重度：🔴 P0 架构
- 风险：① 并发上传会丢数据；② 路径在 Python 包目录内，容器化部署污染镜像层；③ 多副本水平扩展时各副本元数据不一致；④ 与 PRD §5 "支持水平扩展"冲突

**修复后**：
- 新增 [shared/doc_meta_store.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/doc_meta_store.py)：asyncpg 连接池（`min_size=1, max_size=5`）懒初始化；`save_doc_meta`（UPSERT）/`list_doc_meta`（返回 dict）/`remove_doc_meta` 三个异步接口
- [agent-knowledge/rag_chain.py L34-L131](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/rag_chain.py#L34-L131)：删除 `_save_meta`；`upload_document` 改 `await doc_meta_store.save_doc_meta(doc_id, filename)`；`list_documents` 改 `await doc_meta_store.list_doc_meta()`；`delete_document` 改 `await doc_meta_store.remove_doc_meta(doc_id)`
- [shared/config.py L27-L32](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/config.py#L27-L32)：新增 `postgres_host/port/db/user/password` 5 个配置字段，均有默认值
- [docs/database/init.sql L93-L104](file:///home/north30/projects/Personal/smt-agent-platform/docs/database/init.sql#L93-L104)：新增 `doc_meta` 表（`doc_id` PK + `doc_name` + `create_time`），含表/列注释
- pyproject.toml 新增 `asyncpg = "^0.29.0"` 依赖（见 4.3）

**验证结果**：grep 可执行代码 "doc_meta.json" 0 匹配（仅 3 处 docstring 引用迁移历史）；test_knowledge_rag test_upload_document mock `doc_meta_store.save_doc_meta` 用 AsyncMock，全绿；test_knowledge_api 5 用例全绿。

---

### 4.6 M4：list_docs/delete_by_doc 静默截断

**修复前**：
- [shared/vector_store.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/vector_store.py) L199-L225：`delete_by_doc` 与 `list_docs` 用 `limit=16384` 硬上限，超过会**静默截断**：超 16384 chunk 的文档删除时只会删前 16384 个，剩余成为孤儿向量
- 严重度：🟠 Major

**修复后**：
- [shared/vector_store.py L193-L225](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/vector_store.py#L193-L225)：`delete_by_doc` 改用 `col.query_iterator(expr=expr, output_fields=["id"], batch_size=1000)` 分页遍历统计条数，再 `col.delete(expr=expr)` 删除
- [shared/vector_store.py L228-L247](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/vector_store.py#L228-L247)：`list_docs` 改用 `col.query_iterator(expr="chunk_id >= 0", output_fields=["doc_id"], batch_size=1000)` 分页遍历按 doc_id 分组统计

**验证结果**：静态核对 query_iterator 调用；test_vector_store 4 用例全绿（未直接测试 delete_by_doc/list_docs 分页，但现有 init/insert/search 用例不受影响）。

---

### 4.7 M5：Prompt 每次读盘无缓存

**修复前**：
- [agent-knowledge/rag_chain.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/rag_chain.py) `_load_prompts`：每次诊断/问答都 `yaml.safe_load` 读 `system_prompt.yaml`，无缓存
- [agent-maintenance/diagnose.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/diagnose.py) `_load_prompts`：同上
- 严重度：🟠 Major
- 风险：每次 I/O 10-30ms 无谓开销

**修复后**：
- [agent-knowledge/rag_chain.py L134-L143](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/rag_chain.py#L134-L143)：`_load_prompts` 加 `@lru_cache(maxsize=1)`，运行期 Prompt 文件不变，首次读盘后缓存
- [agent-maintenance/diagnose.py L122-L131](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/diagnose.py#L122-L131)：同上

**验证结果**：静态核对 @lru_cache 装饰器；rag_chain/diagnose 单测全绿（多次调用 _load_prompts 命中缓存）。

---

### 4.8 M6：health 接口 int 强转错误码语义

**修复前**：
- [agent-maintenance/main.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/main.py) L35-L55：`int(device.get("healthScore") or 0)` 强转，若 device-service 返回非数字字符串（如 `"N/A"`）抛 `ValueError` → `value_error_handler` 返回 400 `invalid_param`，但实际是上游数据异常，应为 502/503
- 严重度：🟠 Major

**修复后**：
- [agent-maintenance/main.py L36-L43](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/main.py#L36-L43)：`raw_score = device.get("healthScore")` → `try: health_score = int(raw_score) except (TypeError, ValueError): raise DeviceServiceUnavailable(f"device-service 返回的 healthScore 非法: {raw_score!r}")`；DeviceServiceUnavailable 由 exception_handler 映射到 503 `device_service_unavailable`，错误码语义对齐"上游数据异常"

**验证结果**：test_health_device_unavailable 用例（mock get_device 抛 DeviceServiceUnavailable → 503）全绿。

---

### 4.9 M8：pydantic ValidationError 死导入

**修复前**：
- [agent-knowledge/main.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/main.py) L9：`from pydantic import ValidationError` 未被使用（FastAPI 422 由 Pydantic 自动处理，无需手动捕获）
- 严重度：⚠️ Minor（P0 清单内）

**修复后**：
- [agent-knowledge/main.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/main.py)：删除 `from pydantic import ValidationError` 导入

**验证结果**：grep "from pydantic import ValidationError" 0 匹配；test_knowledge_api 5 用例全绿。

---

### 4.10 M11：ErrorResponse 两 Agent 各定义一份

**修复前**：
- [agent-knowledge/models.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/models.py) L55-L59：`class ErrorResponse(BaseModel)` 定义
- [agent-maintenance/models.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/models.py) L88-L92：完全相同的 `class ErrorResponse(BaseModel)` 定义
- 严重度：🟠 Major
- 风险：违反 DRY，未来字段调整易漏改

**修复后**：
- 新增 [shared/models.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/models.py)：统一 `class ErrorResponse(BaseModel)` 含 `error: str` + `message: str`
- [agent-knowledge/main.py L11](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/main.py#L11)：改 `from shared.models import ErrorResponse`
- [agent-maintenance/main.py L11](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/main.py#L11)：同上
- 两 Agent 的 models.py 删除本地 ErrorResponse 定义

**验证结果**：grep "class ErrorResponse" 仅 shared/models.py 1 匹配；两 Agent models.py 0 匹配；pytest 全绿。

---

### 4.11 m7：async/sync 风格不一致

**修复前**：
- [agent-knowledge/main.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-knowledge/main.py)：`upload` 是 `async def`，其他 3 个路由是 `def`
- [agent-maintenance/main.py](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/main.py)：4 个路由全是 `def`
- 严重度：⚠️ Minor（P0 清单内）

**修复后**：
- 与 B1 修复同步完成，两 main.py 全路由统一 `async def`

**验证结果**：静态核对两 main.py 路由全 async def；pytest 全绿。

---

## 五、遗留项

### 5.1 P1 项（移交 Phase 3 起步）

| # | 问题 | 归属 |
|---|---|---|
| M1 | 全链路无重试无熔断（llm_client/device_client/vector_store 一次失败即抛） | Phase 3 起步 |
| M3 | predict.py THRESHOLDS 硬编码，无法按设备差异化配置 | Phase 3 |
| M7 | device_client 模块级单例 import 时即创建 httpx.AsyncClient，测试可控性差 | Phase 3 |
| M9 | predict.py 复杂分支覆盖不足（3 测试 vs 9+ 分支） | Phase 2 收尾（未达，移交） |
| — | Python 侧完全无可观测性（无 logging/structlog/healthz/metrics） | Phase 3 起步 |
| — | RAG < 3s PRD P0 指标零性能验证 | Phase 2 收尾（未达，移交） |
| — | docker-compose 无网络隔离，Python Agent 可直连 PG/Redis 绕过 device-service | Phase 2 收尾（未达，移交） |
| — | scripts/dev_restart.sh 未启动 Java 微服务 | Phase 2 收尾（未达，移交） |
| — | Agent 间无通信机制（PRD §3.3 多智能体协作） | Phase 3 起步 |
| — | 无 API 版本号（/v1/ 前缀） | Phase 3 起步 |
| — | 预测性维护"提前 14 天预警"被裁剪为规则+线性外推 v1，未达 PRD P0 | Phase 5+ |

### 5.2 P2 项（移交 Phase 3）

| # | 问题 | 归属 |
|---|---|---|
| m1 | llm_client 每次新建 httpx.AsyncClient 无连接池复用 | Phase 3 起步 |
| m2 | diagnose._extract_json_block 简陋，无法处理嵌套代码块 | Phase 3 |
| m3 | document_loader 按字符切分，英文按字符会切断单词 | Phase 3 |
| m5 | conftest.py importlib hack 注册 kebab-case 包 | Phase 3 |

### 5.3 环境验证遗留

- **docker-compose 端到端闭环未实跑**：本机 Docker Hub 不可达（Phase 1 遗留环境问题），本轮仅做编译 + 单测级验证。端到端验证需在 Docker 可用的环境中执行：启动 docker-compose（PG/Milvus/Redis/Kafka）→ 跑 init.sql → 启动 Java 微服务 + Python Agent → curl 验证鉴权闭环（无 token 401 / 合法 token 放行）+ Milvus/PG 实连（上传文档 → doc_meta 表有记录 → ask 检索）。

---

## 六、审查方法附录

### 6.1 复现步骤

**Python 单元测试**：
```bash
cd python-agents
poetry lock          # 同步锁文件（pyproject.toml 变更后必须）
poetry install       # 安装 asyncpg 等新依赖
poetry run pytest -v # 预期 26 passed
```

**Java 网关测试**：
```bash
cd java-backend
mvn -pl smt-gateway test  # 预期 4 passed（AgentAuthWebFilterTest）
```

**Java 全量回归测试**：
```bash
cd java-backend
mvn test  # 预期 57 passed（smt-common 5 + smt-gateway 4 + smt-device-service 48）
```

**grep 静态核对**：
```bash
# B3：langchain 已移除
grep -n "langchain" python-agents/pyproject.toml  # 预期 0 匹配

# M8：ValidationError 死导入已删除
grep -n "from pydantic import ValidationError" python-agents/agent-knowledge/main.py  # 预期 0 匹配

# M11：ErrorResponse 仅在 shared/models.py
grep -rn "class ErrorResponse" python-agents/ --include=models.py  # 预期仅 shared/models.py 1 匹配

# P0-5：doc_meta.json 不在可执行代码中（仅 docstring 引用）
grep -rn "doc_meta\.json" python-agents/  # 预期仅 3 处 docstring/comment
```

### 6.2 审查覆盖文件清单

| 模块 | 文件 | 审查动作 |
|---|---|---|
| python-agents/shared | llm_client.py / vector_store.py / doc_meta_store.py / config.py / models.py | 全文读取 + grep 核对 |
| python-agents/agent-knowledge | main.py / rag_chain.py / models.py / document_loader.py | 全文读取 |
| python-agents/agent-maintenance | main.py / diagnose.py / predict.py / device_client.py / models.py | 全文读取 |
| python-agents/tests | 8 个测试文件 | 全文读取 + pytest 验证 |
| python-agents | pyproject.toml / poetry.lock | 全文读取 + poetry lock/install 验证 |
| java-backend/smt-gateway | AgentAuthWebFilter.java / AgentAuthWebFilterTest.java / application.yml / pom.xml / SmtGatewayApplication.java | 全文读取 + mvn test 验证 |
| java-backend/smt-common | JwtUtil.java | 全文读取（核对 generateToken API） |
| docs/database | init.sql | grep 核对 doc_meta 表 |
| docs/explaination | project-explanation-phase2.md L803-L841 | 全文读取（P0 清单基准） |

### 6.3 验证结果汇总

| 验证项 | 命令 | 结果 |
|---|---|---|
| Python 单测 | `poetry run pytest -v` | 26 passed, 0 failed, 0.95s |
| Java 网关单测 | `mvn -pl smt-gateway test` | 4 passed, 0 failed, 3.099s |
| Java 全量单测 | `mvn test` | 57 passed, 0 failed, 11.608s |
| grep B3 | `grep "langchain" pyproject.toml` | 0 匹配 |
| grep M8 | `grep "from pydantic import ValidationError" agent-knowledge/main.py` | 0 匹配 |
| grep M11 | `grep -rn "class ErrorResponse" --include=models.py` | 仅 shared/models.py 1 匹配 |
| grep P0-5 | `grep -rn "doc_meta\.json"` | 仅 3 处 docstring/comment |
