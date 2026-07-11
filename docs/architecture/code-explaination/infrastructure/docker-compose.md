# Docker Compose 基础设施

> docker-compose 服务编排，定义 SMT 平台所需的全部中间件和基础设施服务。

**模块路径**: `docker-compose/`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/docker-compose/docker-compose.yml`

---

## 服务列表

| 服务 | 镜像 | 端口 | 网络 | 说明 |
|------|------|------|------|------|
| postgres | postgres:16 | 5432 | intranet | 关系型数据库 |
| redis | redis:7 | 6379 | intranet | 缓存 |
| zookeeper | zookeeper:3.4.6 | 2181 | intranet | Kafka 依赖 |
| kafka | kafka:2.13-2.7.1 | 9092 | intranet | 消息队列 |
| etcd | etcd:3.5 | 2379 | intranet | Milvus 依赖 |
| minio | minio/minio | 9000 | intranet | Milvus 存储 |
| milvus | milvusdb/milvus:2.4 | 19530 | intranet | 向量数据库 |
| influxdb | influxdb:2.7 | 8086 | intranet | 时序数据库 |
| mosquitto | eclipse-mosquitto:2.0.18 | 1883 | edge | MQTT Broker |

---

## 网络

| 网络名 | 说明 |
|--------|------|
| `intranet` | 内网服务（PG, Redis, Kafka, Milvus 等） |
| `edge` | 边缘设备通信（MQTT Broker） |
| `app` | 应用服务（预留） |

---

## 初始化脚本

| 文件 | 说明 |
|------|------|
| `init/01-schema.sql` | 数据库表结构初始化 |
| `init/02-seed-devices.sql` | 设备种子数据 |

---

## 常用命令

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 查看日志
docker compose logs -f [service_name]

# 重启单个服务
docker compose restart [service_name]
```
