import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Wildcard CORS"):
        Settings(cors_origins=["*"])


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"debug": True}, "Debug mode"),
        ({}, "must not point to localhost"),
        (
            {
                "database_url": "postgresql+psycopg://postgres:postgres@db.example/test",
            },
            "Default database credentials",
        ),
        (
            {
                "database_url": "postgresql+psycopg://app:secret@db.example/test",
                "trusted_hosts": ["*"],
            },
            "Wildcard trusted hosts",
        ),
    ],
)
def test_unsafe_production_settings_are_rejected(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(environment="production", **overrides)


def test_safe_production_settings_are_accepted() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://app:secret@db.example/test",
        trusted_hosts=["api.example.com"],
        cors_origins=["https://app.example.com"],
    )

    assert settings.environment == "production"
