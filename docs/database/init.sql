-- =============================================================================
-- SMT 设备服务数据库初始化脚本（PostgreSQL）
--
-- 创建 device、device_data_point、device_data 三张表及索引，含中文注释。
-- 字段与 smt-device-service 实体严格对齐。
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
-- 索引
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_device_data_point_device_id ON device_data_point (device_id);
CREATE INDEX IF NOT EXISTS idx_device_data_query ON device_data (device_id, datapoint_code, timestamp);
CREATE INDEX IF NOT EXISTS idx_device_data_timestamp ON device_data (timestamp);

