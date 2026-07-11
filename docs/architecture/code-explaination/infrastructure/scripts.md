# Scripts 自动化脚本

> 项目自动化脚本集合，提供构建、启动、停止、测试等功能。

**模块路径**: `scripts/`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/scripts/`

---

## 脚本清单

| 脚本 | 说明 |
|------|------|
| `build_all.sh` | 全量构建（Java → Python） |
| `start_all.sh` | 启动所有本地服务 |
| `stop_all.sh` | 停止所有本地服务 |
| `dev_restart.sh` | 重启所有本地服务 |
| `api_integration_test.sh` | API 接口集成测试 |
| `init_db.sh` | 数据库初始化 |
| `config.sh` | 共享配置变量 |

---

## 常用命令

```bash
# 全量构建
bash scripts/build_all.sh

# 启动所有服务
bash scripts/start_all.sh

# 停止所有服务
bash scripts/stop_all.sh

# 重启所有服务
bash scripts/dev_restart.sh

# 运行集成测试
bash scripts/api_integration_test.sh
```
