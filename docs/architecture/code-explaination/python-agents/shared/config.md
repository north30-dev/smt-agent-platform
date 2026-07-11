# config

> 应用配置模块，使用 pydantic-settings 从 `.env` 加载配置，所有字段均提供默认值。

**模块路径**: `shared/config.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/config.py`

---

## 模块级对象

### `settings`

全局单例 `Settings` 实例，在模块加载时自动创建。

---

## 类

### `Settings(BaseSettings)`

> 应用配置类，字段与 `.env` 环境变量一一对应

**签名**: `class Settings(BaseSettings)`

**配置模型**: `SettingsConfigDict(env_file=".env", extra="ignore")`

#### 配置字段

**LLM 配置**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `llm_provider` | `str` | `"tongyi"` | LLM 提供商 |
| `llm_api_key` | `str` | `""` | API Key |
| `llm_base_url` | `str` | `"https://dashscope.aliyuncs.com/compatible-mode/v1"` | API 基础 URL |
| `llm_model` | `str` | `"qwen-plus"` | 对话模型 |
| `llm_embed_model` | `str` | `"text-embedding-v2"` | 嵌入模型 |
| `llm_max_retries` | `int` | `3` | 最大重试次数 |
| `llm_retry_backoff` | `float` | `1.0` | 重试退避秒数 |

**Milvus 配置**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `milvus_host` | `str` | `"localhost"` | Milvus 主机 |
| `milvus_port` | `int` | `19530` | Milvus 端口 |
| `milvus_max_retries` | `int` | `2` | 最大重试次数 |
| `milvus_retry_backoff` | `float` | `1.0` | 重试退避秒数 |

**PostgreSQL 配置**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `postgres_host` | `str` | `"localhost"` | 数据库主机 |
| `postgres_port` | `int` | `5432` | 数据库端口 |
| `postgres_db` | `str` | `"smt"` | 数据库名 |
| `postgres_user` | `str` | `"smt"` | 数据库用户 |
| `postgres_password` | `str` | `"smt123"` | 数据库密码 |

**设备服务配置**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `device_service_base_url` | `str` | `"http://localhost:8081"` | 设备服务地址 |
| `device_service_max_retries` | `int` | `2` | 最大重试次数 |

**预测维护配置**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `predict_thresholds` | `dict` | `{TEMP: {max:80, high:60}, VIB: {max:15, high:10}, DEFAULT: {max:100, high:80}}` | 阈值配置 |
| `predict_min_span_hours` | `int` | `24` | 最小数据跨度（小时） |
| `predict_window_size` | `int` | `100` | 滑动窗口大小 |
| `predict_trend_threshold` | `float` | `0.01` | 趋势判定阈值 |

**质量分析配置**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `quality_aoi_defect_rate_threshold` | `float` | `0.02` | AOI 缺陷率阈值 |
| `quality_spi_solder_paste_volume_min` | `float` | `50.0` | SPI 锡膏体积下限 |
| `quality_spi_solder_paste_volume_max` | `float` | `150.0` | SPI 锡膏体积上限 |
| `quality_monitor_window_hours` | `int` | `1` | 监控时间窗口（小时） |
| `quality_alerts_page_size` | `int` | `20` | 告警分页大小 |

**调度配置**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `scheduler_max_horizon_hours` | `int` | `72` | 排产最大时间范围 |
| `scheduler_changeover_minutes` | `int` | `30` | 换线时间（分钟） |
| `scheduler_device_min_health_score` | `int` | `85` | 设备最低健康评分 |
| `scheduler_capacity_per_hour` | `int` | `1000` | 每小时产能 |

**Kafka 配置**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kafka_bootstrap_servers` | `str` | `"localhost:9092"` | Kafka 地址 |
| `kafka_consumer_group` | `str` | `"smt-execution-group"` | 消费者组 |
| `kafka_topic_device_anomaly` | `str` | `"device.anomaly"` | 设备异常 Topic |
| `kafka_topic_execution_instruction` | `str` | `"execution.instruction"` | 执行指令 Topic |
| `kafka_topic_exception_record` | `str` | `"exception.record"` | 异常记录 Topic |
| `kafka_enabled` | `bool` | `True` | 是否启用 Kafka |

---

## 顶层函数

### `_default_predict_thresholds() -> dict`

> 返回默认预测阈值配置

**签名**: `def _default_predict_thresholds() -> dict`

**返回值**: `dict` — 包含 TEMP、VIB、DEFAULT 三种类型的阈值配置
