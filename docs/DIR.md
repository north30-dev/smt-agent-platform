你的项目需要一个清晰、完整的骨架来支撑三语言（Java + Python + C++）加前端的开发。以下是一份**带详细注释**的完整目录结构文档，涵盖从根目录到各模块的每一层文件夹与关键配置文件。

你可以将其作为**搭建指南**，直接对照创建；未来新增业务代码时，也请严格遵守这套分层规则。

---

# 📁 项目目录结构完整文档

## 项目名称：`smt-agent-platform`  
**技术栈**：Java 21 (Spring Boot) + Python 3.12 (LangChain) + C++17 (CMake) + React/TS (Vite)  
**适用场景**：SMT贴片产线智能运维与调度（工业级Agent平台）

---

## 一、项目根目录（Root）

```text
smt-agent-platform/                     # 【项目根目录】
├── README.md                           # 项目介绍、技术选型、快速启动指南
├── .gitignore                          # Git忽略规则（必须包含：target/ __pycache__/ build/ node_modules/ .env）
├── .editorconfig                       # 统一代码风格（缩进、换行符）
│
├── docker-compose/                     # 【容器编排】所有中间件一键拉起
│   ├── docker-compose.yml              # 定义：Kafka, Redis, PostgreSQL, Milvus, InfluxDB
│   └── .env                            # 中间件端口、账号、密码（不提交Git）
│
├── api-contracts/                      # 【跨语言契约】定义服务间通信协议
│   ├── grpc/
│   │   └── agent_service.proto         # Java ↔ Python 的gRPC接口定义（生成双端代码）
│   └── openapi/
│       └── device_api.yaml             # RESTful API文档（用于前端联调与Mock）
│
├── scripts/                            # 【自动化脚本】环境初始化、构建、部署
│   ├── setup_wsl_env.sh                # WSL2下安装JDK/Poetry/CMake/Docker
│   ├── build_all.sh                    # 按序编译：C++ → Java → Python（打包）
│   └── dev_restart.sh                  # 开发时一键重启所有服务（含docker-compose down/up）
│
├── docs/                               # 【项目文档】非代码资料
│   ├── PRD.md                          # 产品需求文档（你之前写过的那份）
│   ├── architecture/
│   │   └── system_design.puml          # PlantUML架构图（四层架构+多智能体协作）
│   └── database/
│       └── er_diagram.puml             # 数据库ER图（设备/工单/质量表关系）
│
├── frontend/                           # 【前端可视化】（React + TypeScript）
│   └── ...（详见下文第二节）
│
├── java-backend/                       # 【Java稳定底座】（Spring Cloud微服务群）
│   └── ...（详见下文第三节）
│
├── python-agents/                      # 【Python智能大脑】（LangGraph多智能体）
│   └── ...（详见下文第四节）
│
└── cpp-native/                         # 【C++底层胶水】（工业协议解析 + 高性能算法）
    └── ...（详见下文第五节）
```

---

## 二、前端模块（`frontend/`）

> **职责**：提供产线看板、设备监控、排产操作、知识问答等人机交互界面。  
> **建议**：**你不必深入CSS/样式**，重点放在`services/`层（对接后端API）和`pages/`路由配置。

```text
frontend/
├── package.json                        # npm依赖（React 18, Vite 5, Ant Design 5, ECharts 5, Axios）
├── vite.config.ts                      # 构建配置：代理 `/api` → Java网关(8080)，支持HMR
├── tsconfig.json                       # TypeScript编译配置（严格模式）
├── index.html                          # 单页入口
├── .env.development                    # 开发环境变量：VITE_API_BASE_URL=http://localhost:8080
├── .env.production                     # 生产环境变量：VITE_API_BASE_URL=/api（同域部署）
│
├── public/                             # 静态资源（不经过构建）
│   └── favicon.ico
│
└── src/
    ├── main.tsx                        # 入口文件：挂载React根组件
    ├── App.tsx                         # 根组件：配置路由（react-router-dom）
    │
    ├── layouts/                        # 布局组件（包裹页面内容）
    │   └── DashboardLayout.tsx         # 侧边栏+顶栏+内容区（使用Ant Design Layout）
    │
    ├── pages/                          # 页面视图（对应PRD功能模块）
    │   ├── Dashboard/                  # 产线总览大屏（核心看板）
    │   ├── DeviceMonitor/              # 设备健康监控与预测维护界面
    │   ├── QualityControl/             # 质量缺陷实时监控与根因追溯
    │   ├── ProductionSchedule/         # 智能排产结果展示与手动调整
    │   ├── KnowledgeBase/              # RAG知识库问答界面（类似ChatGPT风格）
    │   └── AlarmCenter/                # 告警列表与处理闭环
    │
    ├── components/                     # 公共UI组件（可复用）
    │   ├── Charts/                     # ECharts封装（折线图、仪表盘、柱状图）
    │   └── CommonTable/                # 带搜索/分页的通用表格
    │
    ├── services/                       # 【重要】对接后端API
    │   ├── api.ts                      # Axios实例（拦截器：添加JWT Token，统一错误提示）
    │   ├── deviceApi.ts                # 调用 `/api/device/*` 接口
    │   ├── orderApi.ts                 # 调用 `/api/order/*` 接口
    │   └── agentApi.ts                 # 调用 `/api/agent/*` 接口（经Java网关转发至Python）
    │
    ├── stores/                         # 全局状态管理（Zustand）
    │   ├── useDeviceStore.ts           # 设备列表/在线状态
    │   └── useUserStore.ts             # 用户信息/权限
    │
    └── utils/                          # 工具函数
        └── format.ts                   # 时间格式化、数字单位转换（秒→时:分:秒）
```

---

## 三、Java后端模块（`java-backend/`）

> **职责**：设备数据采集、工单管理、消息路由、权限认证 —— **所有稳定的业务底座**。  
> **构建工具**：Maven（多模块）  
> **命名规则**：模块名（文件夹）用 `kebab-case`（如`smt-common`），包名用 `com.smt.platform.xxx`

```text
java-backend/
├── pom.xml                             # 父POM：定义Spring Boot版本(3.2.x)、公共依赖（Lombok, MyBatis-Plus）
│
├── smt-common/                         # 【基础工具模块】无业务逻辑，被所有微服务依赖
│   ├── pom.xml
│   └── src/main/java/com/smt/platform/common/
│       ├── utils/                      # 工具类：JWT令牌、AES加解密、日期处理
│       ├── config/                     # 全局配置：Jackson序列化、跨域CORS
│       └── exception/                  # 全局异常处理器与自定义业务异常
│
├── smt-gateway/                        # 【API网关】所有外部请求入口（Spring Cloud Gateway）
│   ├── pom.xml
│   └── src/main/java/com/smt/platform/gateway/
│       └── routes/                     # 路由配置：/api/device→device-service，/api/agent→agent-router
│
├── smt-device-service/                 # 【设备服务】管理设备台账、采集配置、实时数据接收
│   ├── pom.xml
│   └── src/main/java/com/smt/platform/device/
│       ├── controller/                 # REST接口：设备列表、健康状态查询
│       ├── service/                    # 业务逻辑：设备注册、数据解析
│       ├── mapper/                     # MyBatis-Plus Mapper（操作PostgreSQL设备表）
│       └── model/                      # 实体类（Device, DeviceDataPoint）
│
├── smt-order-service/                  # 【工单服务】生产工单与排程结果管理
│   ├── pom.xml
│   └── src/main/java/com/smt/platform/order/
│       ├── controller/                 # 工单创建、进度上报
│       └── service/                    # 调用Python调度Agent（通过Feign或gRPC）
│
├── smt-quality-service/                # 【质量服务】AOI缺陷数据接收与统计
│   ├── pom.xml
│   └── src/main/java/com/smt/platform/quality/
│       └── service/                    # 缺陷率计算、触发质量Agent分析
│
├── smt-notification-service/           # 【通知服务】统一推送（钉钉、企微、邮件）
│   ├── pom.xml
│   └── src/main/java/com/smt/platform/notification/
│       └── service/                    # 根据告警级别选择渠道推送
│
└── smt-agent-router/                   # 【AI路由中转】Java→Python的桥梁（gRPC客户端）
    ├── pom.xml
    └── src/main/java/com/smt/platform/router/
        ├── grpc/                       # 从api-contracts生成的gRPC Stub
        └── service/                    # 封装调用Python Agent的方法
```

---

## 四、Python智能体模块（`python-agents/`）

> **职责**：调度、运维、质量、知识、执行 —— **五个核心Agent协同决策**。  
> **依赖管理**：uv（`pyproject.toml`，PEP 621）
> **运行方式**：每个Agent作为独立FastAPI服务（端口8001~8005）

```text
python-agents/
├── pyproject.toml                      # 根配置：声明langchain, fastapi, grpcio, pydantic等依赖
├── uv.lock                             # 依赖锁定（自动生成，不手动修改）
├── .env                                # 环境变量（大模型API_KEY, Milvus地址）—— 不提交Git
├── README.md                           # Python模块说明：各Agent端口映射表
│
├── shared/                             # 【公共模块】所有Agent共享
│   ├── __init__.py
│   ├── llm_client.py                   # 统一大模型调用（支持通义/DeepSeek/GLM切换）
│   ├── vector_store.py                 # Milvus连接与向量检索封装（含embedding）
│   └── prompts/                        # 系统级提示词
│       └── system_prompt.yaml          # 基础角色设定（如“你是SMT产线运维专家”）
│
├── agent-scheduler/                    # 【调度智能体】端口8001
│   ├── __init__.py
│   ├── main.py                         # FastAPI启动（路由：/schedule/optimize）
│   └── tools/                          # 专属工具函数
│       └── capacity_calculator.py      # 计算产线剩余产能
│
├── agent-maintenance/                  # 【运维智能体】端口8002
│   ├── __init__.py
│   ├── main.py                         # 接口：/maintenance/predict
│   └── phm_model.py                    # 预测性维护算法（调用C++ .so库做信号处理）
│
├── agent-quality/                      # 【质量分析智能体】端口8003
│   ├── __init__.py
│   ├── main.py                         # 接口：/quality/root-cause
│   └── root_cause_analyzer.py          # 基于知识图谱的根因定位
│
├── agent-knowledge/                    # 【知识助手RAG】端口8004
│   ├── __init__.py
│   ├── main.py                         # 接口：/knowledge/ask（流式输出）
│   ├── rag_chain.py                    # 构建RAG流程：检索→重排→生成
│   └── data/                           # 文档库（待向量化）
│       └── manuals/                    # 设备操作手册（PDF/Word）
│
├── agent-execution/                    # 【执行协同智能体】端口8005
│   ├── __init__.py
│   └── main.py                         # 接口：/execution/dispatch（下发维修工单）
│
├── protos/                             # 【gRPC生成代码】从api-contracts编译
│   ├── __init__.py
│   └── agent_service_pb2_grpc.py       # gRPC服务端/客户端骨架
│
└── tests/                              # 单元测试
    └── test_llm_client.py
```

---

## 五、C++原生模块（`cpp-native/`）

> **职责**：工业协议解析（Modbus/S7）、高性能信号处理（FFT）—— **作为Python/Java的动态库**。  
> **构建工具**：CMake（输出`.so`或`.dll`）  
> **关键**：**只生成库文件，不生成可执行文件**。

```text
cpp-native/
├── CMakeLists.txt                      # 顶级CMake：指定C++17，查找pybind11和JNI
├── cmake/
│   └── FindPybind11.cmake              # 辅助脚本（定位pybind11库路径）
│
├── third_party/                        # 【第三方工业协议源码】（通过git submodule引入）
│   ├── open62541/                      # OPC UA开源实现
│   └── libmodbus/                      # Modbus协议库
│
├── include/                            # 【对外头文件】其他模块需要引用的接口定义
│   ├── protocol/
│   │   └── modbus_parser.h
│   └── algorithm/
│       └── fft_filter.h
│
├── src/
│   ├── protocol/                       # 【协议解析实现】
│   │   ├── CMakeLists.txt
│   │   ├── modbus_parser.cpp           # 解析Modbus帧，提取寄存器值
│   │   └── s7_comm_parser.cpp          # 解析西门子S7协议
│   │
│   ├── algorithm/                      # 【算法实现】
│   │   ├── CMakeLists.txt
│   │   └── fft_filter.cpp              # 快速傅里叶变换（用于振动信号分析）
│   │
│   └── bindings/                       # 【胶水层】暴露给Python/Java的接口
│       ├── CMakeLists.txt              # 编译动态库：libnative_processor.so
│       ├── pybind_module.cpp           # pybind11封装：将C++函数绑定到Python
│       └── jni_wrapper.cpp             # JNI封装：供Java调用的C++函数入口
│
└── build/                              # 【编译输出目录】（自动生成，git忽略）
    ├── lib/                            # 生成的动态库文件（.so/.dll）
    └── obj/                            # 编译中间文件（.o）
```

---

## 📌 模块间协作关系（快速索引）

| 调用方向 | 协议/方式 | 涉及目录 |
| :--- | :--- | :--- |
| **前端 → Java** | HTTP REST (`/api/*`) | `frontend/services/*.ts` → `java-backend/smt-gateway` |
| **Java → Python** | gRPC 或 Kafka 异步 | `smt-agent-router` → `python-agents/agent-*/main.py` |
| **Python → C++** | pybind11 (直接import `.so`) | `python-agents/agent-maintenance/phm_model.py` → `cpp-native/build/lib/*.so` |
| **Java → C++** | JNI (需加载动态库) | `java-backend/smt-device-service` → `cpp-native/build/lib/*.so`（较少用） |

---
