from pydantic import computed_field
from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL, make_url


class RuntimeConfig(BaseSettings):
    """Configuration for runtime settings."""

    SERVER_NAME: str = "localhost:5000"
    """The server name."""

    SECRET_KEY: str = "sample_secret_key"
    """A secret key for cryptographic operations."""

    POSTGRES_USER: str = "mapuser"
    """PostgreSQL database username."""

    POSTGRES_HOST: str = "localhost"
    """PostgreSQL database host."""

    POSTGRES_PORT: int = 5432
    """PostgreSQL database port."""

    POSTGRES_PASSWORD: str = "mappass"
    """PostgreSQL database password."""

    POSTGRES_DB: str = "mapdb"
    """PostgreSQL database name."""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> URL:
        """Database connection URI for SQLAlchemy."""
        return make_url(
            f"postgresql+psycopg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    """URL for the Celery message broker."""

    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    """URL for the Celery result backend."""

    @computed_field
    @property
    def CELERY(self) -> dict[str, str | bool]:
        """Celery configuration dictionary."""
        return {
            "broker_url": self.CELERY_BROKER_URL,
            "result_backend": self.CELERY_RESULT_BACKEND,
            "task_ignore_result": True,
        }

    MAP_CORE_BASE_URL: str = "https://map-core.example.com"
    """Base URL for the mAP Core service."""

    WEB_UI_SP_CERT_PATH: str = "./certs/server.crt"
    """Path to the mAP SP certificate."""

    WEB_UI_SP_KEY_PATH: str = "./certs/server.key"
    """Path to the mAP SP private key."""


config = RuntimeConfig()
"""runtime configuration instance."""
