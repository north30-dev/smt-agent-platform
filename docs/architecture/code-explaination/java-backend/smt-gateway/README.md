# smt-gateway 模块

> API 网关模块，基于 Spring Cloud Gateway（响应式），提供路由代理、JWT 认证过滤和 CORS 配置。

**模块路径**: `java-backend/smt-gateway/`
**包根路径**: `com.smt.platform.gateway`
**端口**: 8080

## 职责

- 统一入口：路由转发至 device-service 和 Python agents
- JWT 认证：对 `/api/agent/**` 路径进行 Token 校验
- CORS 跨域：开发环境跨域支持

## 包结构

```
com.smt.platform.gateway/
├── SmtGatewayApplication.java    ← 启动类
├── security/
│   └── AgentAuthWebFilter.java   ← JWT 认证过滤器
└── config/
    └── CorsConfig.java           ← CORS 配置
```

## 依赖关系

- **依赖**: `smt-common`（JwtUtil）
- **转发目标**: smt-device-service (8081), agent-scheduler (8001), agent-maintenance (8002), agent-quality (8003), agent-knowledge (8004), agent-orchestrator (8005)

## 快速导航

| 文件 | 说明 |
|------|------|
| [SmtGatewayApplication](SmtGatewayApplication.md) | Spring Boot 启动类 |
| [AgentAuthWebFilter](filter/AgentAuthWebFilter.md) | JWT 认证 WebFilter |
| [CorsConfig](config/CorsConfig.md) | CORS 跨域配置 |
