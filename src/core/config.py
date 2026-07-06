from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


import pathlib
import os

class Settings(BaseSettings):
    APP_NAME: str = "Archon"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,https://archon-inky.vercel.app"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/archon_test"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str | None) -> str | None:
        if v:
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_REQUEST_TIMEOUT: float = 20.0
    WORKTREE_CACHE_DIR: str = ".archon_cache/worktrees"
    USE_REDIS_QUEUE: bool = False  # Set True only when a dedicated worker process is running
    
    PROJECT_ROOT: str = pathlib.Path(os.path.abspath(__file__)).parent.parent.parent.as_posix()

    API_AUTH_TOKEN: str | None = None
    WEBHOOK_SECRET: str | None = None
    WEBHOOK_RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1)
    SECRET_ENCRYPTION_KEY: str | None = None
    JWT_SECRET_KEY: str = "archon-dev-secret-change-in-production"
    FRONTEND_URL: str = "https://archon-inky.vercel.app"

    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "qwen2.5"
    LLM_FALLBACK_MODEL: str = "google/gemma-2-9b-it:free"
    LLM_FALLBACK_PROVIDERS: str = "openrouter,mock"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com/v1"
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"

    # ── NVIDIA NIM (build.nvidia.com) ──────────────────────────────────────
    NVIDIA_API_KEY: str | None = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Per-agent NVIDIA NIM model assignments
    # Planner: orchestration & routing — strong instruction-following model
    NVIDIA_PLANNER_MODEL: str = "deepseek-ai/deepseek-v4-pro"
    # Architecture: boundary & layer analysis — advanced reasoning
    NVIDIA_ARCHITECTURE_MODEL: str = "deepseek-ai/deepseek-v4-pro"
    # Maintainability: complexity & tech debt — large context comprehension
    NVIDIA_MAINTAINABILITY_MODEL: str = "deepseek-ai/deepseek-v4-flash"
    # Technical Debt: forecasting structural drag — balanced performance
    NVIDIA_DEBT_MODEL: str = "nvidia/nemotron-3-ultra"
    # Impact: blast radius & risk — specialized for analysis tasks
    NVIDIA_IMPACT_MODEL: str = "deepseek-ai/deepseek-v4-pro"
    # Synthesis: final report aggregation — fast, efficient
    NVIDIA_SYNTHESIS_MODEL: str = "deepseek-ai/deepseek-v4-flash"

    EMBEDDING_PROVIDER: str = "ollama"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    WEBHOOK_IDEMPOTENCY_TTL_SECONDS: int = Field(default=300, ge=1)

    VCS_PROVIDER: str = "logging"
    GITHUB_TOKEN: str | None = None
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_OAUTH_CLIENT_ID: str | None = None
    GITHUB_OAUTH_CLIENT_SECRET: str | None = None
    GITHUB_OAUTH_REDIRECT_URI: str = "https://archon-ixrh.onrender.com/api/v1/oauth/github/callback"
    GITLAB_API_URL: str = "https://gitlab.com"
    GITLAB_OAUTH_CLIENT_ID: str | None = None
    GITLAB_OAUTH_CLIENT_SECRET: str | None = None
    GITLAB_OAUTH_REDIRECT_URI: str = "https://archon-ixrh.onrender.com/api/v1/oauth/gitlab/callback"

    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    OTEL_SERVICE_NAME: str = "archon"

    PORT: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
