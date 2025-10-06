from pydantic_settings import BaseSettings


class RuntimeConfig(BaseSettings):
    """Configuration for runtime settings."""

    SECRET_KEY: str = "sample_secret_key"
    """A secret key for cryptographic operations."""


config = RuntimeConfig()
