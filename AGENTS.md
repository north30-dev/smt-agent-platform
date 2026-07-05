# AGENTS.md

本文件用于约束 AI Agent 在本仓库中的行为。所有 Agent 在执行任务前必须先阅读本文件。

***

## 一、项目概述

**项目名称**：smt-agent-platform —— SMT 贴片产线智能运维与调度系统

**定位**：面向电子制造 SMT 生产线的工业智能体平台，通过多智能体协同（调度、运维、质量、知识、执行）实现"感知—决策—规划—执行"全链路运营闭环。

**技术栈与版本**：

| 层          | 技术                                               | 版本                |
| ---------- | ------------------------------------------------ | ----------------- |
| Java 后端    | Spring Boot / Spring Cloud + Maven 多模块           | Java 21           |
| Python 智能体 | LangChain / LangGraph + FastAPI + uv             | Python 3.12       |
| C++ 原生层    | CMake + pybind11 + JNI（仅输出动态库）                   | C++17             |
| 前端         | React + TypeScript + Vite + Ant Design + ECharts | React 18 / Vite 5 |
| 中间件        | Kafka、Redis、PostgreSQL、InfluxDB、Milvus           | docker-compose 编排 |

**目录骨架**：见 `docs/DIR.md`，四层架构 = 交互层 / 智能体层 / 服务层 / 数据层。

***

## 二、构建与测试命令

所有命令均在项目根目录 `smt-agent-platform/` 下执行。

### 2.1 中间件（开发环境）

```bash
cd docker-compose
docker-compose up -d
docker-compose down
```

### 2.2 C++ 原生层（最先编译）

```bash
cd cpp-native
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

产物：`cpp-native/build/lib/libnative_processor.so`

### 2.3 Java 后端

```bash
cd java-backend
mvn clean install -DskipTests        # 全量编译安装
mvn -pl smt-device-service spring-boot:run   # 单服务运行
mvn test                             # 全量测试
mvn -pl smt-common test              # 单模块测试
```

### 2.4 Python 智能体

```bash
cd python-agents
uv sync
uv run pytest                    # 全部测试
uv run pytest tests/test_llm_client.py  # 单文件测试
uv run uvicorn agent-maintenance.main:app --port 8002 --reload  # 运行单个 Agent
```

### 2.5 前端

```bash
cd frontend
npm install
npm run dev        # 开发模式（端口 5173，代理 /api → 8080）
npm run build      # 生产构建
npm run lint
npx tsc --noEmit   # 类型检查
```

### 2.6 一键脚本

```bash
bash scripts/build_all.sh       # C++ → Java → Python 全量构建
bash scripts/dev_restart.sh     # 重启所有本地服务
```

***

## 三、代码风格与规范

**只列出与本语言默认风格不同的强制规则**：

### 3.1 Java

- Maven 模块名（文件夹）一律用 `kebab-case`：`smt-common`、`smt-device-service`
- Java 包名一律用 `com.smt.platform.<模块>`：`com.smt.platform.device`
- 实体类必须用 MyBatis-Plus 注解，不用 JPA
- 所有 REST 接口路径以 `/api/<模块>/*` 为前缀

### 3.2 Python

- 包名/目录名用 `kebab-case`（`agent-maintenance`），与 Java 模块对齐
- Python 导入用下划线模块名（`main.py` 内 `from shared.llm_client import ...`）
- 强制使用 Pydantic 做请求/响应模型校验
- 大模型调用统一走 `shared/llm_client.py`，禁止在各 Agent 内直接 new client

### 3.3 C++

- 只产出动态库（`.so`/`.dll`），**禁止生成可执行文件**
- 对外接口头文件放在 `cpp-native/include/`，实现放 `src/`
- Python 绑定走 pybind11，Java 绑定走 JNI，二者在 `src/bindings/` 内隔离

### 3.4 前端

- 页面目录用 `PascalCase`（`DeviceMonitor/`），组件文件用 `PascalCase.tsx`
- API 调用统一放 `src/services/`，禁止在组件内直接 `axios`
- 全局状态用 Zustand，禁止引入 Redux

### 3.5 通用

- 缩进统一 4 空格（前端 2 空格）；换行符统一 `LF`
- 文件末尾必须保留一个空行

***

## 四、安全与边界

### 4.1 绝对禁止修改/读取后外泄的文件

- `docker-compose/.env`
- `python-agents/.env`（含大模型 API\_KEY、Milvus 地址）
- `frontend/.env.development`、`frontend/.env.production`
- 任何包含密钥、密码、Token 的 `*.key`、`*.pem`、`credentials.*` 文件

以上文件**只允许在用户明确要求且已确认的情况下修改**，禁止在对话中回显其完整内容。

### 4.2 需要用户确认才能执行的操作

- `git push`、`git push --force`、`git reset --hard`、`git branch -D`
- 删除目录、`rm -rf`、`docker-compose down -v`（删卷）
- 修改 `pom.xml` / `pyproject.toml` / `CMakeLists.txt` / `package.json` 的依赖版本
- 新增 Maven 模块、新增 Python Agent、新增前端页面目录
- 任何对 `api-contracts/` 下 `.proto` / `.yaml` 的修改（影响跨语言生成代码）
- 直接操作生产数据库 / 生产 Kafka

### 4.3 数据安全

- 严禁把真实产线数据写入示例代码或测试用例
- 测试数据须使用脱敏的 mock 值
- 大模型调用禁止把 `.env` 中的 KEY 硬编码进源码

***

## 五、Git 工作流

### 5.1 分支命名

- `main`：生产分支，只接受合并，禁止直接 push
- `develop`：集成分支
- `feature/<模块>-<简述>`：新功能，如 `feature/scheduler-urgent-order`
- `fix/<模块>-<简述>`：bug 修复
- `refactor/<模块>-<简述>`：重构
- `docs/<简述>`：仅文档改动

### 5.2 提交信息格式（Conventional Commits）

```
<type>(<scope>): <subject>

<body 可选>
```

- `type`：`feat` / `fix` / `refactor` / `docs` / `test` / `chore` / `build` / `ci`
- `scope`：模块名，如 `scheduler` / `device-service` / `phm` / `frontend`
- `subject`：祈使句、中文或英文均可，≤50 字符，结尾不加句号

示例：

```
feat(scheduler): 急单插单自动评估与换线建议
fix(device-service): 设备健康评分计算空指针异常
docs(agent): 补充运维 Agent 接口说明
```

### 5.3 其他

- 提交前本地跑过对应模块的 `test` 与 `lint`
- 单次提交只覆盖一个逻辑变更，禁止"大杂烩"提交
- PR 描述必须包含：变更目的、影响范围、测试方式
- 提交人配置：`user.name=north30-dev`，`user.email=north30dev@163.com`

***

## 六、报告输出规范

### 6.1 输出位置

所有由 AI Agent 生成的审查、扫描、评估类报告**统一输出到** `.trae/reports/` 目录。禁止散落在仓库根目录、`docs/` 或其他位置。

- 目录路径：`.trae/reports/`
- 目录不存在时由 Agent 自行 `mkdir -p` 创建，无需用户确认
- 该目录由 Agent 维护，不参与 `docs/` 文档站点构建

### 6.2 命名规范

文件名格式：`<报告类型>-<阶段或范围>.md`

- 全部小写，单词用 `kebab-case` 连接
- `<报告类型>` 见 §6.3 清单
- `<阶段或范围>` 用 `phase1` / `phase2` / `<模块名>` / `release-<版本号>` 等明确边界

示例：

| 文件名                                | 含义                    |
| ---------------------------------- | --------------------- |
| `prd-conformance-review-phase1.md` | Phase 1 PRD 符合性审查     |
| `security-scan-phase1.md`          | Phase 1 安全扫描          |
| `code-review-device-service.md`    | device-service 模块代码审查 |
| `performance-eval-release-v0.2.md` | v0.2 版本性能评估           |

### 6.3 报告类型清单

| 报告类型      | 文件名前缀                     | 触发场景             |
| --------- | ------------------------- | ---------------- |
| PRD 符合性审查 | `prd-conformance-review-` | 阶段交付完成、对照 PRD 验收 |
| 安全扫描      | `security-scan-`          | 阶段交付完成、提交前、定期复审  |
| 代码审查      | `code-review-`            | 模块级 / PR 级代码质量审查 |
| 性能评估      | `performance-eval-`       | 版本发布前、性能瓶颈定位     |
| 架构评审      | `architecture-review-`    | 跨阶段架构演进、重大重构     |
| 测试报告      | `test-report-`            | 阶段测试汇总、回归测试      |

新增报告类型须先在本表登记，禁止 Agent 自创前缀。

### 6.4 内容要求

1. **语言**：中文输出（含标题、表格、结论）
2. **元信息表**：报告首部必须含表格，列出审查对象、对照基准（如有）、审查方法、审查日期、审查范围、评估口径/置信度阈值
3. **结论先行**：第一章给出总体结论（符合/不符合、findings 数量、关键风险），后续章节展开细节
4. **findings 表格**：安全扫描类报告必须使用 skill 规定的列结构（`# | Category | Title | Severity | Confidence | Evidence | Recommendation | Location`）
5. **文件引用**：所有代码位置引用使用 `file:///` 绝对路径 + `#Lstart-Lend` 行号范围链接，禁止裸 `行号` 或裸相对路径
6. **敏感数据脱敏**：报告内禁止出现真实凭据、密钥、Token 明文；引用配置文件时用 `<redacted>` 或截断占位
7. **改进建议**：含优先级（P0/P1/P2）与建议归属阶段
8. **审查方法附录**：末尾附审查步骤，便于复现

### 6.5 提交与生命周期

- 报告文件可纳入 git 管理（不属于 §4.1 禁止文件）
- 报告生成后**不自动随业务代码提交**，须由用户明确指示
- 旧阶段报告不删除，作为历史审计留痕；新版同名报告覆盖前须确认

### 6.6 禁止行为

- ❌ 在对话中回显报告全文（应输出到文件后给出路径链接）
- ❌ 把报告内容塞入 `docs/` 主文档站点
- ❌ 在报告中写入补丁代码（安全类报告遵循 skill §9.2 "Recommendation is prose, not code"）
- ❌ 跳过 §6.4 元信息表直接展开细节

