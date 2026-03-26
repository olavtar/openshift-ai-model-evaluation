# This project was developed with assistance from AI tools.
"""Application configuration via pydantic-settings."""

import logging
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "openshift-ai-model-evaluation"
    DEBUG: bool = False

    # CORS
    ALLOWED_HOSTS: list[str] = ["http://localhost:5173"]

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://user:password@localhost:5432/ai-quickstart-template"
    )

    # Model serving (MaaS defaults)
    MAAS_ENDPOINT: str = "https://maas.apps.prod.rhoai.rh-aiservices-bu.com"
    MODEL_API_TOKEN: str = ""
    MODEL_A_NAME: str = "granite-3.1-8b-instruct"
    MODEL_A_DEPLOYMENT_MODE: str = "maas"
    MODEL_B_NAME: str = "llama-3.1-8b-instruct"
    MODEL_B_DEPLOYMENT_MODE: str = "maas"

    # Embedding model
    EMBEDDING_MODEL: str = "nomic-embed-text-v1.5"

    # Judge model for evaluation scoring (uses MaaS endpoint)
    JUDGE_MODEL_NAME: str = "granite-3.1-8b-instruct"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def validate_api_token(self) -> Self:
        """Warn if MODEL_API_TOKEN is not set."""
        if not self.MODEL_API_TOKEN:
            logger.warning(
                "MODEL_API_TOKEN is not set. LLM calls will fail. "
                "Set MODEL_API_TOKEN environment variable to enable model serving."
            )
        return self


settings = Settings()
