# API调用链路示例

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 十三、API调用链路示例

### 13.1 设备故障处理完整链路

```bash
# 1. 用户触发故障处理
curl -X POST http://localhost:8005/v1/orchestrator/device_fault \
  -H "Content-Type: application/json" \
  -d '{"device_id":1,"symptom":"温度异常"}'

# 2. Orchestrator调用Maintenance诊断
curl -X POST http://localhost:8002/v1/maintenance/diagnose \
  -H "Content-Type: application/json" \
  -d '{"device_id":1,"symptom":"温度异常"}'

# 3. Maintenance查询Java设备信息
curl http://localhost:8081/api/device/1

# 4. Maintenance调用LLM推理
curl -X POST http://localhost:1234/v1/chat/completions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"model":"google/gemma-4-e4b","messages":[{"role":"user","content":"分析设备温度异常原因"}]}'

# 5. Orchestrator调用Quality分析影响
curl -X POST http://localhost:8003/v1/quality/root_cause \
  -H "Content-Type: application/json" \
  -d '{"device_id":1,"defect_description":"设备异常可能导致质量问题"}'

# 6. Quality调用Knowledge检索历史案例
curl -X POST http://localhost:8004/v1/knowledge/cases/search \
  -H "Content-Type: application/json" \
  -d '{"query":"温度异常导致焊接不良","top_k":5}'

# 7. Orchestrator调用Scheduler调整计划
curl -X POST http://localhost:8001/v1/scheduler/suggest \
  -H "Content-Type: application/json" \
  -d '{"orders":["ORD-20260707-001"],"constraints":{"production_lines":["LINE-1"]}}'

# 8. 创建执行指令
curl -X POST http://localhost:8006/v1/execution/command \
  -H "Content-Type: application/json" \
  -d '{"command_type":"MAINTENANCE","target_device_id":1,"description":"更换轴承","priority":"HIGH"}'
```

### 13.2 调用链路图

```
用户/前端
    │
    ▼
Gateway (8080)
    │
    ├─→ Device Service (8081) ─→ PostgreSQL
    │
    ├─→ Orchestrator (8005)
    │       │
    │       ├─→ Maintenance (8002) ─→ Device Service ─→ LLM Service
    │       ├─→ Quality (8003) ─→ Knowledge (8004) ─→ Milvus
    │       ├─→ Scheduler (8001) ─→ PostgreSQL
    │       └─→ Execution (8006) ─→ PostgreSQL
    │
    └─→ Knowledge (8004) ─→ Milvus + LLM Service
```
