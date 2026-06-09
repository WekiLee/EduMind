"""配置管理 —— 应用设置"""

from pydantic_settings import BaseSettings


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
    llm_provider: str = "openai-compatible"
    llm_model: str = "deepseek-v4-flash"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.deepseek.com/v1"
    ollama_base_url: str = "http://localhost:11434"

    # ── Embedding ──
    # provider: "local" (sentence-transformers) | "litellm" (远程API)
    embedding_provider: str = "local"
    # local 模型: all-MiniLM-L6-v2 / all-mpnet-base-v2 / ...
    # litellm 模型: text-embedding-ada-002 / openai/text-embedding-3-small / ollama/nomic-embed-text / ...
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384  # all-MiniLM-L6-v2 维度; ada-002 用 1536

    # ── 服务 ──
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    data_dir: str = "./data"

    # ── 内容管道 ──
    max_upload_size_mb: int = 50
    supported_extensions: str = ".pdf,.md,.txt,.docx,.pptx"

    # ── 语音 ──
    whisper_model_size: str = "base"

    # ── 搜索编排 ──
    search_provider: str = "duckduckgo"
    search_api_url: str = ""
    search_max_results: int = 5

    # ── 上下文管理 ──
    context_max_tokens: int = 4096
    context_recent_messages: int = 6
    context_summary_threshold: int = 12
    cache_ttl_seconds: int = 3600
    session_cache_ttl: int = 7200

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
