#!/bin/bash
# 手动初始化 PostgreSQL（适用于已有数据卷，Docker init 不会自动执行的场景）
# 用法：在项目根目录执行 bash scripts/init_db.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

echo "==> 创建 Phase 3 表..."
docker exec -i "$PG_CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < python-agents/shared/db_schema.sql

echo "==> 插入测试设备数据..."
docker exec -i "$PG_CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < docker-compose/init/02-seed-devices.sql

echo "==> 验证表与数据..."
docker exec "$PG_CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
  SELECT 'device' AS table_name, COUNT(*) FROM device WHERE deleted=0
  UNION ALL
  SELECT 'production_orders', COUNT(*) FROM production_orders
  UNION ALL
  SELECT 'quality_alerts', COUNT(*) FROM quality_alerts;
"
echo "==> 数据库初始化完成"
