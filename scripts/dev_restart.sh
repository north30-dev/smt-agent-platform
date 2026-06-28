#!/usr/bin/env bash
# 一键重启所有本地开发服务（中间件 + 各语言服务）
# 用法: bash scripts/dev_restart.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========== [1/4] 重启中间件 =========="
cd "$PROJECT_ROOT/docker-compose"
docker-compose down
docker-compose up -d
cd "$PROJECT_ROOT"

echo "========== [2/4] 重启 C++ 原生层 =========="
echo "[SKIP] cpp-native 暂未实现，跳过"

echo "========== [3/4] 重启 Java 后端 =========="
echo "[TODO] 各微服务请通过 mvn -pl <module> spring-boot:run 单独启动"

echo "========== [4/4] 重启 Python 智能体 =========="
echo "[SKIP] python-agents 暂未实现，跳过"

echo "========== 本地服务重启完成 =========="
