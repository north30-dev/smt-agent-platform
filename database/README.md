# 数据库脚本目录

PostgreSQL 数据库的 DDL、种子数据与维护脚本。

## 目录结构

```
database/
├── README.md                        # 本文件
├── cleanup.sql                      # 清理测试脏数据（手动执行）
├── init/                            # docker-compose 挂载，首次启动自动执行
│   ├── 01-schema.sql                # 全量 DDL（11 张表 + 索引）
│   └── 02-seed-devices.sql          # 设备种子数据（4 台设备）
└── seeds/                           # 可选种子数据（手动执行）
    ├── 03-seed-datapoints.sql       # 设备采集点定义
    ├── 04-seed-quality-baseline.sql # 质量基线参数（预留）
    └── 05-seed-knowledge.md         # 知识库样例文档（通过 API 上传）
```

## 使用方式

### 全新环境（自动）

```bash
docker compose up -d
# PostgreSQL 镜像自动执行 init/ 下的 SQL（按字母序）
```

### 已有数据卷（手动）

```bash
bash scripts/init_db.sh          # 重建 schema + 种子数据
bash scripts/init_db.sh --clean  # 清理测试数据 → 重建 → 重插种子
```

### 单独执行清理

```bash
docker exec -i smt-postgres psql -U smt -d smt < database/cleanup.sql
```

### 单独执行种子数据

```bash
docker exec -i smt-postgres psql -U smt -d smt < database/seeds/03-seed-datapoints.sql
```

### 上传知识库文档

```bash
curl -X POST http://localhost:8080/api/agent/v1/knowledge/upload \
  -F "file=@database/seeds/05-seed-knowledge.md"
```

## 表结构概览

| 表名 | 用途 | 写入方 |
|------|------|--------|
| device | 设备台账 | init/02-seed + Java device-service |
| device_data_point | 设备采集点配置 | seeds/03 + Java device-service |
| device_data | 设备时序数据 | Java device-service（MQTT/OPC UA 采集） |
| doc_meta | 知识库文档元数据 | Python agent-knowledge |
| quality_alerts | 质量告警 | Python agent-quality |
| production_orders | 生产工单 | Python agent-scheduler |
| production_plans | 排产计划 | Python agent-scheduler |
| execution_instructions | 执行指令 | Python agent-execution |
| exception_records | 异常记录 | Python agent-execution |
| approvals | 审批记录 | Python agent-execution |
| workflows | 工作流 | Python agent-orchestrator |

## 枚举值速查

**device.device_type**: `PRINTER` / `MOUNTER` / `REFLOW` / `AOI` / `SPI` / `OTHER`

**device.protocol_type**: `OPC_UA` / `MQTT`

**device.status**: `RUNNING` / `STOPPED` / `MAINTENANCE` / `IDLE`

**production_orders.priority**: `NORMAL` / `HIGH` / `URGENT`

**production_orders.status**: `PENDING` / `PLANNED` / `IN_PROGRESS` / `COMPLETED` / `CANCELLED`

**execution_instructions.type**: `REPAIR` / `PRODUCTION_ADJUST` / `PARAM_CHANGE`

**execution_instructions.status**: `PENDING` / `PENDING_APPROVAL` / `APPROVED` / `REJECTED` / `EXECUTING` / `COMPLETED` / `FAILED`

**workflows.status**: `RUNNING` / `SUCCESS` / `FAILED`
