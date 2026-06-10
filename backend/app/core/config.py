"""配置管理 —— 应用设置"""

from pydantic import model_validator
from pydantic_settings import BaseSettings


DEFAULT_DATABASE_URL = "postgresql+asyncpg://edumind:edumind_dev@localhost:5432/edumind"
DEFAULT_NEO4J_PASSWORD = "edumind_dev"
DEFAULT_JWT_SECRET = "change-this-in-production"
INSECURE_JWT_SECRETS = {
    DEFAULT_JWT_SECRET,
    "edumind-dev-secret",
    "edumind-dev-secret-change-in-production",
}


class Settings(BaseSettings):
    environment: str = "development"

    # ── 数据库 ──
    database_url: str = DEFAULT_DATABASE_URL
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = DEFAULT_NEO4J_PASSWORD
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT ──
    jwt_secret: str = DEFAULT_JWT_SECRET
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
    default_admin_password: str | None = None

    # ── 内容管道 ──
    max_upload_size_mb: int = 50
    supported_extensions: str = ".pdf,.md,.txt,.docx,.pptx"

    # ── 语音 ──
    whisper_model_size: str = "base"
    tts_provider: str = "edge-tts"  # edge-tts | kokoro

    # ── 搜索编排 ──
    search_provider: str = "duckduckgo"
    search_api_url: str = ""
    search_max_results: int = 5

    # ── MCP ──
    mcp_enabled: bool = False  # 是否启用 MCP 工具
    mcp_servers: str = ""  # JSON 格式: [{"name":"web-search","command":"npx","args":["-y","@mcp-server/web-search"]}]

    # ── 上下文管理 ──
    context_max_tokens: int = 4096
    context_recent_messages: int = 6
    context_summary_threshold: int = 12
    cache_ttl_seconds: int = 3600
    session_cache_ttl: int = 7200

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """生产环境禁止继续使用开发默认密钥。"""
        if self.environment.lower() not in {"prod", "production"}:
            return self

        insecure_fields = []
        if self.jwt_secret in INSECURE_JWT_SECRETS or len(self.jwt_secret) < 32:
            insecure_fields.append("JWT_SECRET")
        if self.database_url == DEFAULT_DATABASE_URL or "edumind_dev" in self.database_url:
            insecure_fields.append("DATABASE_URL")
        if self.neo4j_password == DEFAULT_NEO4J_PASSWORD:
            insecure_fields.append("NEO4J_PASSWORD")

        if insecure_fields:
            joined = ", ".join(insecure_fields)
            raise ValueError(f"生产环境禁止使用默认开发密钥或密码: {joined}")
        return self


settings = Settings()
