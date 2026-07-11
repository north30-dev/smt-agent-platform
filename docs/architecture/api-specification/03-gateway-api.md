# Java Gateway API

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 三、Java Gateway API

### 3.1 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | smt-gateway |
| 技术栈 | Spring Cloud Gateway（响应式） |
| 端口 | 8080 |
| 职责 | 所有外部请求入口，路由转发至后端服务 |

### 3.2 路由规则

| 路径模式 | 目标服务 | 端口 | StripPrefix |
|---------|---------|------|------------|
| `/api/device/**` | smt-device-service | 8081 | 0（保留原路径） |
| `/api/agent/v1/knowledge/**` | agent-knowledge | 8004 | 2（剥离 `/api/agent`） |
| `/api/agent/v1/maintenance/**` | agent-maintenance | 8002 | 2 |
| `/api/agent/v1/quality/**` | agent-quality | 8003 | 2 |
| `/api/agent/v1/scheduler/**` | agent-scheduler | 8001 | 2 |
| `/api/agent/v1/orchestrator/**` | agent-orchestrator | 8005 | 2 |
| `/api/agent/v1/execution/**` | agent-execution | 8006 | 2 |

### 3.3 路由转发示例

```
外部请求: GET /api/device/list
→ 转发至: http://localhost:8081/api/device/list

外部请求: GET /api/agent/v1/knowledge/docs
→ StripPrefix 剥离 /api/agent
→ 转发至: http://localhost:8004/v1/knowledge/docs
```

### 3.4 JWT 鉴权

| 项目 | 值 |
|------|-----|
| 鉴权范围 | `/api/agent/**` 路径 |
| Token 位置 | `Authorization: Bearer <token>` |
| 密钥 | 与 device-service 共用 `SMT_JWT_SECRET` 环境变量 |
| 校验方式 | 网关 Reactive WebFilter 拦截校验 |

### 3.5 健康检查

**端点**: `GET /actuator/health`

```json
{
  "status": "UP",
  "components": {
    "gateway": {"status": "UP"}
  }
}
```

---

**配置文件**: `java-backend/smt-gateway/src/main/resources/application.yml`
