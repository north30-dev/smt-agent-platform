-- 开发环境种子数据：4 台 SMT 设备
-- 字段名与 Device.java 实体（snake_case 映射）对齐
-- device_type 枚举值取自 Device.java 注释：PRINTER/MOUNTER/REFLOW/AOI/SPI/OTHER
-- protocol_type 枚举值：OPC_UA/MQTT
-- status 枚举值：RUNNING/STOPPED/MAINTENANCE/IDLE
INSERT INTO device (
    device_code, device_name, device_type, production_line,
    ip_address, protocol_type, status, health_score,
    create_time, update_time, deleted
) VALUES
    ('DEV-001', '贴片机A', 'MOUNTER', 'LINE-1', '192.168.1.101', 'MQTT', 'RUNNING', 95, NOW(), NOW(), 0),
    ('DEV-002', '回流焊B', 'REFLOW', 'LINE-1', '192.168.1.102', 'OPC_UA', 'RUNNING', 88, NOW(), NOW(), 0),
    ('DEV-003', 'AOI检测仪C', 'AOI', 'LINE-2', '192.168.1.103', 'MQTT', 'RUNNING', 92, NOW(), NOW(), 0),
    ('DEV-004', 'SPI检测仪D', 'SPI', 'LINE-2', '192.168.1.104', 'MQTT', 'IDLE', 90, NOW(), NOW(), 0)
ON CONFLICT (device_code) DO NOTHING;
