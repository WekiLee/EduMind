"""应用配置 —— 从环境变量读取，带默认值"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── 数据库 ──
    database_url: str = "postgresql+asyncpg://edumind:edumind_dev@localhost:5432/edumind"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "edumind_dev"
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT ──
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 72

    # ── LLM ──
    # 默认使用 DeepSeek 公开 API；可切换为 ollama 本地
    llm_provider: str = "openai-compatible"  # openai-compatible | ollama
    llm_model: str = "deepseek-v4-flash"
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.deepseek.com/v1"
    ollama_base_url: str = "http://localhost:11434"  # 本地可选

    # ── 服务 ──
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    data_dir: str = "./data"

    # ── 内容管道 ──
    max_upload_size_mb: int = 50
    supported_extensions: str = ".pdf,.md,.txt,.docx,.pptx"

    # ── 上下文管理 ──
    context_max_tokens: int = 4096          # 送入 LLM 的上下文最大 token 数
    context_recent_messages: int = 6        # 至少保留的最近消息数
    context_summary_threshold: int = 12     # 超过此消息数触发摘要压缩
    cache_ttl_seconds: int = 3600           # LLM 响应缓存有效期（1h）
    session_cache_ttl: int = 7200           # 会话上下文 Redis 缓存（2h）

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
