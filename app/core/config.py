from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
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
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/management_task"
    database_echo: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    oauth_state_secret: SecretStr = SecretStr("development-only-change-me")
    oauth_state_cookie_name: str = "mt_oauth"
    oauth_state_max_age_seconds: int = Field(default=600, ge=300, le=1_800)
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str | None = None
    allowed_google_domains: list[str] = Field(default_factory=list)
    frontend_auth_success_url: str = "http://localhost:3000/auth/callback"
    auth_cookie_name: str = "mt_session"
    csrf_cookie_name: str = "mt_csrf"
    cookie_secure: bool = False
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    session_idle_minutes: int = Field(default=60, ge=5, le=1_440)

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

    @field_validator(
        "google_client_id",
        "google_client_secret",
        "google_redirect_uri",
        mode="before",
    )
    @classmethod
    def blank_oauth_values_are_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_production_safety(self) -> Self:
        has_client_id = self.google_client_id is not None
        has_client_secret = self.google_client_secret is not None
        if has_client_id != has_client_secret:
            raise ValueError("Google client ID and secret must be configured together")

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
        if self.oauth_state_secret.get_secret_value() == "development-only-change-me":
            raise ValueError("Production OAuth state secret must be changed")
        if not self.cookie_secure:
            raise ValueError("Secure cookies are required in production")
        cookie_names = (
            self.oauth_state_cookie_name,
            self.auth_cookie_name,
            self.csrf_cookie_name,
        )
        if any(not name.startswith("__Host-") for name in cookie_names):
            raise ValueError("Production cookie names must use the __Host- prefix")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
