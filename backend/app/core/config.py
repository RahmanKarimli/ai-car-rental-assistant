from functools import lru_cache
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "local"
    app_timezone: str = "Asia/Baku"
    default_language: str = "en"
    app_origin: str = "http://localhost:3000"
    cookie_secure: bool = False
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "rental"
    db_user: str = "rental_app"
    checkpoint_db_user: str = "rental_graph"
    postgres_user: str = "rental_owner"
    database_url: str = ""
    checkpoint_database_url: str = ""
    postgres_password_file: str = "/run/secrets/postgres_password"
    app_database_password_file: str = "/run/secrets/app_database_password"
    graph_database_password_file: str = "/run/secrets/graph_database_password"
    redis_password_file: str = "/run/secrets/redis_password"
    redis_host: str = "redis"
    redis_url: str = ""
    llm_provider: str = "openai"
    embedding_provider: str = "openai"
    openai_api_key: str = ""
    openai_api_key_file: str = "/run/secrets/openai_api_key"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    openai_timeout_seconds: int = 20
    openai_max_retries: int = 2
    openai_max_output_tokens: int = 1200
    openai_rpm_limit: int = 30
    openai_tpm_limit: int = 60000
    chat_context_max_turns: int = 10
    chat_context_max_tokens: int = 6000
    ai_max_concurrency: int = 4
    quote_ttl_seconds: int = 600
    hold_ttl_seconds: int = 600
    quote_signing_key_file: str = "/run/secrets/quote_signing_key"
    fx_refresh_seconds: int = 21600
    chat_retention_months: int = 12
    asset_provider: str = "filesystem"
    asset_root: str = "/data/assets"
    notification_provider: str = "in_app"

    @model_validator(mode="after")
    def valid_configuration(self):
        if self.openai_embedding_dimensions != 1536:
            raise ValueError("This database schema requires 1536-dimensional policy embeddings")
        if self.llm_provider!="openai" or self.embedding_provider!="openai":
            raise ValueError("Register a provider adapter before selecting a different AI provider")
        if self.asset_provider!="filesystem" or self.notification_provider!="in_app":
            raise ValueError("Register a storage/notification adapter before selecting it")
        if self.ai_max_concurrency<1 or self.openai_rpm_limit<1 or self.openai_tpm_limit<1:
            raise ValueError("Concurrency and quota limits must be positive")
        if self.default_language not in {"en","az"}:
            raise ValueError("Supported languages are en and az")
        return self

    def secret(self, file: str) -> str:
        p = Path(file)
        return p.read_text().strip() if p.is_file() else ""

    @property
    def api_key(self) -> str:
        return self.openai_api_key or self.secret(self.openai_api_key_file)

    def db_url(self, owner: bool = False, graph: bool = False) -> str:
        if not owner and not graph and self.database_url:
            return self.database_url
        if graph and self.checkpoint_database_url:
            return self.checkpoint_database_url
        user = self.postgres_user if owner else self.checkpoint_db_user if graph else self.db_user
        file = self.postgres_password_file if owner else self.graph_database_password_file if graph else self.app_database_password_file
        return URL.create("postgresql" if graph else "postgresql+asyncpg", username=user,
                          password=self.secret(file), host=self.db_host, port=self.db_port,
                          database=self.db_name).render_as_string(hide_password=False)

@lru_cache
def settings() -> Settings:
    return Settings()
