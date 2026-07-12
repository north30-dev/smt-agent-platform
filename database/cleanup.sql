-- 清理测试累积的脏数据，保留表结构与设备种子数据
-- 用法：
--   Docker 环境：docker exec -i smt-postgres psql -U smt -d smt < database/cleanup.sql
--   或通过脚本：bash scripts/init_db.sh --clean
--
-- ⚠️ 不要在 docker-compose up 首次初始化时自动执行（此文件不在 init/ 目录下）

-- 按外键依赖顺序反向清理
-- 1. 审批记录（依赖 execution_instructions）
DELETE FROM approvals;

-- 2. 异常记录（依赖 execution_instructions）
DELETE FROM exception_records;

-- 3. 执行指令（依赖 workflows）
DELETE FROM execution_instructions;

-- 4. 工作流
DELETE FROM workflows;

-- 5. 排产计划
DELETE FROM production_plans;

-- 6. 生产工单
DELETE FROM production_orders;

-- 7. 质量告警
DELETE FROM quality_alerts;

-- 8. 知识库文档元数据（Milvus 向量需通过 API 删除，此处仅清 PG 侧记录）
DELETE FROM doc_meta;

-- 9. 设备时序数据
DELETE FROM device_data;

-- 10. 设备采集点配置（清空后需重新通过 API 注册）
DELETE FROM device_data_point;

-- 保留：device 表（4 台种子设备不动）
