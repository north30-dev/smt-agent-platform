#!/usr/bin/env bash
# 一键全量构建：C++ → Java → Python
# 用法: bash scripts/build_all.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========== [1/3] 编译 C++ 原生层 =========="
# C++ 原生层本阶段暂未实现，跳过
echo "[SKIP] cpp-native 暂未实现，跳过 C++ 构建"

echo "========== [2/3] 编译 Java 后端 =========="
cd "$PROJECT_ROOT/java-backend"
mvn clean install -DskipTests
cd "$PROJECT_ROOT"

echo "========== [3/3] 编译 Python 智能体 =========="
# ===== Python 智能体层（Phase 2+）=====
echo "[3/3] 构建 Python agents..."
if [ -d "$PROJECT_ROOT/python-agents" ]; then
    cd "$PROJECT_ROOT/python-agents"
    if command -v poetry >/dev/null 2>&1; then
        poetry install --no-interaction --no-root || echo "警告：poetry install 失败，跳过"
    else
        echo "警告：未检测到 poetry，跳过 Python 依赖安装"
    fi
else
    echo "跳过：python-agents 目录不存在"
fi
cd "$PROJECT_ROOT"

echo "========== 全量构建完成 =========="
