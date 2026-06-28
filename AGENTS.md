# AGENTS.md

本文件用于约束 AI Agent 在本仓库中的行为。所有 Agent 在执行任务前必须先阅读本文件。

---

## 一、项目概述

**项目名称**：smt-agent-platform —— SMT 贴片产线智能运维与调度系统

**定位**：面向电子制造 SMT 生产线的工业智能体平台，通过多智能体协同（调度、运维、质量、知识、执行）实现"感知—决策—规划—执行"全链路运营闭环。

**技术栈与版本**：

| 层 | 技术 | 版本 |
|----|------|------|
| Java 后端 | Spring Boot / Spring Cloud + Maven 多模块 | Java 21 |
| Python 智能体 | LangChain / LangGraph + FastAPI + Poetry | Python 3.14 |
| C++ 原生层 | CMake + pybind11 + JNI（仅输出动态库） | C++17 |
| 前端 | React + TypeScript + Vite + Ant Design + ECharts | React 18 / Vite 5 |
| 中间件 | Kafka、Redis、PostgreSQL、InfluxDB、Milvus | docker-compose 编排 |

**目录骨架**：见 `docs/DIR.md`，四层架构 = 交互层 / 智能体层 / 服务层 / 数据层。

---

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
poetry install
poetry run pytest                    # 全部测试
poetry run pytest tests/test_llm_client.py  # 单文件测试
poetry run uvicorn agent-maintenance.main:app --port 8002 --reload  # 运行单个 Agent
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

---

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

---

## 四、安全与边界

### 4.1 绝对禁止修改/读取后外泄的文件
- `docker-compose/.env`
- `python-agents/.env`（含大模型 API_KEY、Milvus 地址）
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

---

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
