-- Phase 3 数据库 Schema
-- 集中维护 Phase 3 新增的 quality_alerts、production_orders、production_plans 三张表 DDL
-- 以及 REL-1 新增的 workflows 工作流持久化表
-- 在 PostgreSQL 中执行：psql -U smt -d smt -f shared/db_schema.sql

-- 质量告警记录表（agent-quality 写入）
CREATE TABLE IF NOT EXISTS quality_alerts (
    id BIGSERIAL PRIMARY KEY,
    device_id BIGINT NOT NULL,
    defect_rate DOUBLE PRECISION NOT NULL,
    threshold DOUBLE PRECISION NOT NULL,
    status VARCHAR(32) NOT NULL,
    datapoint_code VARCHAR(64),
    alert_time TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quality_alerts_device_id ON quality_alerts(device_id);
CREATE INDEX IF NOT EXISTS idx_quality_alerts_alert_time ON quality_alerts(alert_time);

-- 订单表（agent-scheduler 写入）
CREATE TABLE IF NOT EXISTS production_orders (
    order_id BIGSERIAL PRIMARY KEY,
    order_no VARCHAR(64) NOT NULL UNIQUE,
    product_model VARCHAR(64) NOT NULL,
    quantity INTEGER NOT NULL,
    priority VARCHAR(16) NOT NULL DEFAULT 'NORMAL',
    delivery_date DATE NOT NULL,
    material_ready BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    source VARCHAR(32) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_production_orders_status ON production_orders(status);
CREATE INDEX IF NOT EXISTS idx_production_orders_priority ON production_orders(priority);
CREATE INDEX IF NOT EXISTS idx_production_orders_delivery_date ON production_orders(delivery_date);
CREATE INDEX IF NOT EXISTS idx_production_orders_source ON production_orders(source);

-- 排产计划表（agent-scheduler 写入）
CREATE TABLE IF NOT EXISTS production_plans (
    plan_id BIGSERIAL PRIMARY KEY,
    plan_version INTEGER NOT NULL,
    allocations JSONB NOT NULL,
    description TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_production_plans_status ON production_plans(status);
CREATE INDEX IF NOT EXISTS idx_production_plans_created_at ON production_plans(created_at);

-- 工作流持久化表（REL-1：orchestrator 从内存 dict 迁移到 PG）
-- 由 shared/db.py 的 init_workflow_table() 幂等创建，此处保留 DDL 供手工初始化
CREATE TABLE IF NOT EXISTS workflows (
    workflow_id VARCHAR(64) PRIMARY KEY,
    status VARCHAR(16) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_workflows_created_at ON workflows(created_at);

-- ============================================================================
-- Phase 4 执行闭环表
-- 集中维护 execution_instructions / exception_records / approvals 三张表 DDL
-- 由 shared/db.py 的 init_execution_tables() 幂等创建，此处保留 DDL 供手工初始化
-- ============================================================================

-- 执行指令记录表（agent-execution 写入）
-- 指令类型 REPAIR(维修工单) / PRODUCTION_ADJUST(生产调整) / PARAM_CHANGE(参数变更)
-- 状态流转 PENDING → PENDING_APPROVAL → APPROVED/REJECTED → EXECUTING → COMPLETED/FAILED
CREATE TABLE IF NOT EXISTS execution_instructions (
    id BIGSERIAL PRIMARY KEY,
    instruction_id VARCHAR(64) NOT NULL UNIQUE,
    source_workflow_id VARCHAR(64),
    type VARCHAR(32) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    priority VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    auto_execute BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_execution_instructions_source_workflow_id ON execution_instructions(source_workflow_id);
CREATE INDEX IF NOT EXISTS idx_execution_instructions_status ON execution_instructions(status);
CREATE INDEX IF NOT EXISTS idx_execution_instructions_type ON execution_instructions(type);
CREATE INDEX IF NOT EXISTS idx_execution_instructions_priority ON execution_instructions(priority);

-- 异常记录表（执行闭环异常处置：发现 → 分析 → 处置 → 验证 → 关闭）
-- 来源 instruction_timeout / kafka_event / manual
-- 状态流转 OPEN → ANALYZED → HANDLED → CLOSED
CREATE TABLE IF NOT EXISTS exception_records (
    id BIGSERIAL PRIMARY KEY,
    exception_id VARCHAR(64) NOT NULL UNIQUE,
    source VARCHAR(64) NOT NULL,
    instruction_id VARCHAR(64),
    description TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    analysis JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_exception_records_status ON exception_records(status);
CREATE INDEX IF NOT EXISTS idx_exception_records_instruction_id ON exception_records(instruction_id);
CREATE INDEX IF NOT EXISTS idx_exception_records_source ON exception_records(source);

-- 人工审批记录表（关联 execution_instructions）
-- decision: approve / reject
CREATE TABLE IF NOT EXISTS approvals (
    id BIGSERIAL PRIMARY KEY,
    instruction_id VARCHAR(64) NOT NULL,
    decision VARCHAR(16) NOT NULL,
    approver VARCHAR(64),
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_approvals_instruction_id ON approvals(instruction_id);
