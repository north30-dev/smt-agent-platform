-- Phase 3 数据库 Schema
-- 集中维护 Phase 3 新增的 quality_alerts、production_orders、production_plans 三张表 DDL
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
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_production_orders_status ON production_orders(status);
CREATE INDEX IF NOT EXISTS idx_production_orders_priority ON production_orders(priority);
CREATE INDEX IF NOT EXISTS idx_production_orders_delivery_date ON production_orders(delivery_date);

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
