# This project was developed with assistance from AI tools.
"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "openshift-ai-model-evaluation"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # CORS
    ALLOWED_HOSTS: list[str] = ["http://localhost:5173"]

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://user:password@localhost:5432/ai-quickstart-template"
    )

    model_config = {"env_file": ".env"}


settings = Settings()
