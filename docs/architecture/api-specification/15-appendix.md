# 附录

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 十五、附录

### 15.1 API测试脚本

**位置**: `scripts/api_integration_test.sh`

```bash
bash scripts/api_integration_test.sh
```

### 15.2 数据库初始化脚本

**位置**: `docker-compose/init/`

```bash
docker exec -i smt-postgres psql -U smt -d smt < docker-compose/init/01-schema.sql
docker exec -i smt-postgres psql -U smt -d smt < docker-compose/init/02-seed-devices.sql
```

### 15.3 服务重启命令

**中间件重启**:

```bash
cd docker-compose
docker compose up -d
```

**应用层重启**:

```bash
# Java
cd java-backend
mvn -pl smt-device-service spring-boot:run

# Python Agents
cd python-agents
uv run uvicorn agent-scheduler.main:app --port 8001 &
uv run uvicorn agent-maintenance.main:app --port 8002 &
uv run uvicorn agent-quality.main:app --port 8003 &
uv run uvicorn agent-knowledge.main:app --port 8004 &
uv run uvicorn agent-orchestrator.main:app --port 8005 &
uv run uvicorn agent-execution.main:app --port 8006 &
```
