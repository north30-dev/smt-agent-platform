#!/bin/bash
# 手动初始化 PostgreSQL（适用于已有数据卷，Docker init 不会自动执行的场景）
# 用法：
#   bash scripts/init_db.sh          # 初始化 schema + 种子数据
#   bash scripts/init_db.sh --clean  # 清理测试数据 → 重建 schema → 重插种子数据
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

CLEAN=false
if [[ "${1:-}" == "--clean" ]]; then
    CLEAN=true
fi

if $CLEAN; then
    echo "==> 清理测试数据..."
    docker exec -i "$PG_CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < database/cleanup.sql
fi

echo "==> 创建全量表结构..."
docker exec -i "$PG_CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < database/init/01-schema.sql

echo "==> 插入种子数据..."
docker exec -i "$PG_CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < database/init/02-seed-devices.sql

echo "==> 验证表与数据..."
docker exec "$PG_CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
  SELECT 'device' AS table_name, COUNT(*) FROM device WHERE deleted=0
  UNION ALL
  SELECT 'production_orders', COUNT(*) FROM production_orders
  UNION ALL
  SELECT 'quality_alerts', COUNT(*) FROM quality_alerts;
"
echo "==> 数据库初始化完成"
