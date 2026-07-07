"""应用配置模块。

使用 pydantic-settings 从 .env 加载配置，所有字段均提供默认值，
便于在无 .env 的环境下运行单元测试。
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_predict_thresholds() -> dict:
    """预测阈值默认值，与原 predict.py 硬编码值一致。"""
    return {
        "TEMP": {"max": 80.0, "min": 20.0},
        "VIB": {"max": 5.0, "min": 0.0},
        "DEFAULT": {"max": 100.0, "min": 0.0},
    }


class Settings(BaseSettings):
    """应用配置，字段与 .env 环境变量一一对应。"""

    # 大模型配置
    llm_provider: str = "tongyi"
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-plus"
    llm_embed_model: str = "text-embedding-v2"

    # Milvus 向量库
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # Java device-service 地址（Python Agent 通过 HTTP 调用）
    device_service_base_url: str = "http://localhost:8081"

    # PostgreSQL（P0-5：文档元数据持久化，从 doc_meta.json 迁移）
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "smt"
    postgres_user: str = "smt"
    postgres_password: str = "smt123"

    # M1：重试与熔断配置
    llm_max_retries: int = 3
    llm_retry_backoff: float = 1.0
    device_service_max_retries: int = 2
    milvus_max_retries: int = 2
    milvus_retry_backoff: float = 1.0

    # m1：HTTP 连接池复用
    http_max_connections: int = 100

    # M3：预测参数配置化（原 predict.py 硬编码）
    predict_thresholds: dict = Field(default_factory=_default_predict_thresholds)
    predict_min_span_hours: int = 24
    predict_window_size: int = 100
    predict_trend_threshold: float = 0.01

    # 可观测性
    log_level: str = "INFO"

    # Phase 3：质量分析 Agent 阈值
    quality_aoi_defect_rate_threshold: float = 0.02
    quality_spi_solder_paste_volume_min: float = 50.0
    quality_spi_solder_paste_volume_max: float = 150.0
    quality_monitor_window_hours: int = 1
    quality_alerts_page_size: int = 20

    # Phase 3：调度智能体参数
    scheduler_max_horizon_hours: int = 72
    scheduler_changeover_minutes: int = 30
    scheduler_device_min_health_score: int = 85
    scheduler_capacity_per_hour: int = 1000

    # Phase 3：Agent 编排（orchestrator）调用各子 Agent 的基地址
    agent_maintenance_base_url: str = "http://localhost:8002"
    agent_quality_base_url: str = "http://localhost:8003"
    agent_scheduler_base_url: str = "http://localhost:8001"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# 模块加载时实例化单例配置
settings = Settings()
