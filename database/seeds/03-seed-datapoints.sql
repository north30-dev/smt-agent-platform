-- 设备采集点种子数据
-- 每台设备注册温度、振动、压力等采集点，供 MqttDataCollector / DeviceDataCollector 订阅
-- ⚠️ 手动执行：docker exec -i smt-postgres psql -U smt -d smt < database/seeds/03-seed-datapoints.sql
-- 前置条件：device 表已有 4 台设备（device_id = 1~4）

-- DEV-001 贴片机A（MQTT 协议）
INSERT INTO device_data_point (device_id, datapoint_code, datapoint_name, node_path, data_type, sample_interval_ms)
VALUES
    (1, 'TEMP_NOZZLE',    '吸嘴温度',       'smt/dev-001/temp/nozzle',     'NUMBER', 1000),
    (1, 'VIBR_MAIN',      '主轴振动',       'smt/dev-001/vibration/main',  'NUMBER', 500),
    (1, 'SPEED_PLACE',    '贴装速度',       'smt/dev-001/speed/place',     'NUMBER', 1000),
    (1, 'COUNT_PICKUP',   '拾取计数',       'smt/dev-001/count/pickup',    'NUMBER', 5000),
    (1, 'RATE_DEFECT',    '缺陷率',         'smt/dev-001/quality/defect',  'NUMBER', 10000)
ON CONFLICT DO NOTHING;

-- DEV-002 回流焊B（OPC UA 协议）
INSERT INTO device_data_point (device_id, datapoint_code, datapoint_name, node_path, data_type, sample_interval_ms)
VALUES
    (2, 'TEMP_OVEN',      '炉腔温度',       'ns=2;s=DEV-002.temp.oven',    'NUMBER', 1000),
    (2, 'TEMP_CONVEYOR',  '传送带温度',     'ns=2;s=DEV-002.temp.conv',    'NUMBER', 1000),
    (2, 'SPEED_CONVEYOR', '传送带速度',     'ns=2;s=DEV-002.speed.conv',   'NUMBER', 2000),
    (2, 'PRESSURE_N2',    '氮气压力',       'ns=2;s=DEV-002.pressure.n2',  'NUMBER', 5000)
ON CONFLICT DO NOTHING;

-- DEV-003 AOI检测仪C（MQTT 协议）
INSERT INTO device_data_point (device_id, datapoint_code, datapoint_name, node_path, data_type, sample_interval_ms)
VALUES
    (3, 'RATE_DEFECT',    'AOI缺陷率',      'smt/dev-003/quality/defect',  'NUMBER', 10000),
    (3, 'COUNT_TOTAL',    '检测总数',       'smt/dev-003/count/total',     'NUMBER', 10000),
    (3, 'SCORE_IMAGE',    '图像评分',       'smt/dev-003/image/score',     'NUMBER', 5000)
ON CONFLICT DO NOTHING;

-- DEV-004 SPI检测仪D（MQTT 协议）
INSERT INTO device_data_point (device_id, datapoint_code, datapoint_name, node_path, data_type, sample_interval_ms)
VALUES
    (4, 'RATE_SPI_DEFECT','SPI缺陷率',      'smt/dev-004/quality/defect',  'NUMBER', 10000),
    (4, 'THICK_PASTE',    '锡膏厚度',       'smt/dev-004/paste/thickness', 'NUMBER', 5000),
    (4, 'AREA_COVERAGE',  '覆盖面积比',     'smt/dev-004/paste/coverage',  'NUMBER', 5000)
ON CONFLICT DO NOTHING;
