-- 此文件为数据库唯一 DDL 入口，包含全部 11 张表定义与索引。
-- 全新环境 docker compose up 后，PostgreSQL 镜像通过 /docker-entrypoint-initdb.d 自动按字母序执行
-- database/init/01-schema.sql → 02-seed-devices.sql，确保所有表与种子数据就位。
-- 手动初始化（已有数据卷场景）：bash scripts/init_db.sh

-- =============================================================================
-- Phase 1-2 表
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 设备台账表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device (
    id               BIGSERIAL    PRIMARY KEY,
    device_code      VARCHAR(64)  NOT NULL,
    device_name      VARCHAR(128) NOT NULL,
    device_type      VARCHAR(32),
    production_line  VARCHAR(32),
    ip_address       VARCHAR(64),
    protocol_type    VARCHAR(16),
    opc_ua_endpoint  VARCHAR(256),
    status           VARCHAR(16)  DEFAULT 'RUNNING',
    health_score     INT          DEFAULT 100,
    deleted          SMALLINT     DEFAULT 0,
    create_time      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    update_time      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_device_code UNIQUE (device_code)
);

COMMENT ON TABLE device IS '设备台账表';
COMMENT ON COLUMN device.id IS '设备 ID（主键，自增）';
COMMENT ON COLUMN device.device_code IS '设备编码（全局唯一）';
COMMENT ON COLUMN device.device_name IS '设备名称';
COMMENT ON COLUMN device.device_type IS '设备类型：PRINTER/MOUNTER/REFLOW/AOI/SPI/OTHER';
COMMENT ON COLUMN device.production_line IS '所属产线';
COMMENT ON COLUMN device.ip_address IS '设备 IP 地址';
COMMENT ON COLUMN device.protocol_type IS '通信协议类型：OPC_UA/MQTT';
COMMENT ON COLUMN device.opc_ua_endpoint IS 'OPC UA 端点（仅 protocol_type=OPC_UA 时使用）';
COMMENT ON COLUMN device.status IS '设备状态：RUNNING/STOPPED/MAINTENANCE';
COMMENT ON COLUMN device.health_score IS '健康评分（0-100，分数越高越健康）';
COMMENT ON COLUMN device.deleted IS '软删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN device.create_time IS '创建时间';
COMMENT ON COLUMN device.update_time IS '最近更新时间';

-- -----------------------------------------------------------------------------
-- 设备采集点配置表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_data_point (
    id                 BIGSERIAL    PRIMARY KEY,
    device_id          BIGINT       NOT NULL,
    datapoint_code     VARCHAR(64)  NOT NULL,
    datapoint_name     VARCHAR(128),
    node_path          VARCHAR(256) NOT NULL,
    data_type          VARCHAR(16),
    sample_interval_ms INT          DEFAULT 1000,
    create_time        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE device_data_point IS '设备采集点配置表';
COMMENT ON COLUMN device_data_point.id IS '采集点 ID（主键，自增）';
COMMENT ON COLUMN device_data_point.device_id IS '所属设备 ID';
COMMENT ON COLUMN device_data_point.datapoint_code IS '采集点编码（同一设备下唯一）';
COMMENT ON COLUMN device_data_point.datapoint_name IS '采集点名称';
COMMENT ON COLUMN device_data_point.node_path IS '节点路径（OPC UA NodeId 或 MQTT Topic）';
COMMENT ON COLUMN device_data_point.data_type IS '数据类型：NUMBER/STRING/BOOLEAN';
COMMENT ON COLUMN device_data_point.sample_interval_ms IS '采样周期（毫秒）';
COMMENT ON COLUMN device_data_point.create_time IS '创建时间';

-- -----------------------------------------------------------------------------
-- 设备实时/历史数据表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_data (
    id             BIGSERIAL   PRIMARY KEY,
    device_id      BIGINT      NOT NULL,
    datapoint_code VARCHAR(64) NOT NULL,
    value          VARCHAR(256),
    timestamp      TIMESTAMP   NOT NULL
);

COMMENT ON TABLE device_data IS '设备实时/历史数据表';
COMMENT ON COLUMN device_data.id IS '数据记录 ID（主键，自增）';
COMMENT ON COLUMN device_data.device_id IS '设备 ID';
COMMENT ON COLUMN device_data.datapoint_code IS '采集点编码';
COMMENT ON COLUMN device_data.value IS '数据值（统一用字符串传输，前端按 dataType 转换）';
COMMENT ON COLUMN device_data.timestamp IS '数据采集时间';

-- -----------------------------------------------------------------------------
-- 索引（Phase 1-2）
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_device_data_point_device_id ON device_data_point (device_id);
CREATE INDEX IF NOT EXISTS idx_device_data_query ON device_data (device_id, datapoint_code, timestamp);
CREATE INDEX IF NOT EXISTS idx_device_data_timestamp ON device_data (timestamp);

-- -----------------------------------------------------------------------------
-- 知识库文档元数据表（Phase 2 P0-5：从 doc_meta.json 文件持久化迁移到 PG）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doc_meta (
    doc_id       VARCHAR(256) PRIMARY KEY,
    doc_name     VARCHAR(512) NOT NULL,
    create_time  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE doc_meta IS '知识库文档元数据表（Phase 2 P0-5 从文件迁移）';
COMMENT ON COLUMN doc_meta.doc_id IS '文档唯一标识（与 Milvus 中 doc_id 对齐）';
COMMENT ON COLUMN doc_meta.doc_name IS '原始文件名';
COMMENT ON COLUMN doc_meta.create_time IS '入库时间';

-- =============================================================================
-- Phase 3 表
-- =============================================================================
-- 集中维护 Phase 3 新增的 quality_alerts、production_orders、production_plans 三张表 DDL

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

-- =============================================================================
-- Phase 3 修复：工作流持久化（orchestrator 工作流从内存迁移到 PG）
-- =============================================================================
CREATE TABLE IF NOT EXISTS workflows (
    workflow_id VARCHAR(64) PRIMARY KEY,
    status VARCHAR(16) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_workflows_created_at ON workflows(created_at);
