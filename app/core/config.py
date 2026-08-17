from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Management Task API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/management_task"
    database_echo: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("API prefix must start with '/' and must not end with '/'")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_driver(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("APP_DATABASE_URL must use postgresql+psycopg")
        return value

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_cors(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("Wildcard CORS is not allowed when credentials are enabled")
        return value

    @model_validator(mode="after")
    def validate_production_safety(self) -> Self:
        if self.environment != "production":
            return self

        database = make_url(self.database_url)
        if self.debug:
            raise ValueError("Debug mode cannot be enabled in production")
        if database.host in {None, "localhost", "127.0.0.1"}:
            raise ValueError("Production database must not point to localhost")
        if database.username == "postgres" and database.password == database.username:
            raise ValueError("Default database credentials cannot be used in production")
        if "*" in self.trusted_hosts:
            raise ValueError("Wildcard trusted hosts are not allowed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
