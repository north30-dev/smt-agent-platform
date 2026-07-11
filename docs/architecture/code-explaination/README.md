# 代码说明文档

> 本目录包含 SMT Agent Platform 每个模块的详细代码说明文档，按类/函数级别组织。

## 目录结构

```
code-explaination/
├── README.md                              ← 本文件
├── index.md                               ← 全模块索引
├── java-backend/                          ← Java 后端模块
│   ├── smt-common/                        ← 公共基础模块
│   ├── smt-gateway/                       ← API 网关
│   └── smt-device-service/                ← 设备管理服务
├── python-agents/                         ← Python 智能体模块
│   ├── shared/                            ← 公共模块
│   ├── agent-knowledge/                   ← 知识助手
│   ├── agent-maintenance/                 ← 设备运维
│   ├── agent-quality/                     ← 质量分析
│   ├── agent-scheduler/                   ← 调度智能体
│   └── agent-orchestrator/                ← 多智能体编排
└── infrastructure/                        ← 基础设施
    ├── docker-compose.md
    ├── api-contracts.md
    └── scripts.md
```

## 文档规范

- **详细程度**: API 参考级（类/函数签名、参数、返回值、使用示例）
- **方法覆盖**: 全部记录（public + private + protected）
- **语言**: 中文为主，英文术语保留
- **文件引用**: 使用 `file:///` 绝对路径 + 行号链接

## 阅读顺序

1. 阅读 `index.md` 了解全局视图
2. 按需查阅具体模块文档
3. 每个模块先读 `README.md` 了解职责和包结构
4. 再查阅具体类/函数文档
