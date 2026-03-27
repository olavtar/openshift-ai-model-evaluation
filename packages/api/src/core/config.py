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

    # Model A -- all from .env
    MODEL_A_NAME: str = ""
    MODEL_A_API_TOKEN: str = ""
    MAAS_ENDPOINT_A: str = ""
    MODEL_A_DEPLOYMENT_MODE: str = "maas"

    # Model B -- all from .env
    MODEL_B_NAME: str = ""
    MODEL_B_API_TOKEN: str = ""
    MAAS_ENDPOINT_B: str = ""
    MODEL_B_DEPLOYMENT_MODE: str = "maas"

    # Embedding model -- from .env
    EMBEDDING_MODEL: str = ""
    EMBEDDING_API_TOKEN: str = ""
    EMBEDDING_ENDPOINT: str = ""

    # Judge model for evaluation scoring -- from .env
    JUDGE_MODEL_NAME: str = ""
    JUDGE_API_TOKEN: str = ""
    JUDGE_ENDPOINT: str = ""

    model_config = {"env_file": "../../.env", "extra": "ignore"}

    def get_model_config(self, model_name: str) -> dict:
        """Get endpoint and token for a model by name.

        Returns dict with 'endpoint', 'token' keys.
        Falls back through: exact match -> Model A -> Model B.
        """
        if model_name == self.MODEL_A_NAME:
            return {"endpoint": self.MAAS_ENDPOINT_A, "token": self.MODEL_A_API_TOKEN}
        if model_name == self.MODEL_B_NAME:
            return {"endpoint": self.MAAS_ENDPOINT_B, "token": self.MODEL_B_API_TOKEN}
        # Unknown model -- try Model A config as fallback
        return {"endpoint": self.MAAS_ENDPOINT_A, "token": self.MODEL_A_API_TOKEN}

    @property
    def judge_endpoint(self) -> str:
        """Resolve judge model endpoint. Falls back to matching model config."""
        if self.JUDGE_ENDPOINT:
            return self.JUDGE_ENDPOINT
        cfg = self.get_model_config(self.JUDGE_MODEL_NAME)
        return cfg["endpoint"]

    @property
    def judge_token(self) -> str:
        """Resolve judge model token. Falls back to matching model config."""
        if self.JUDGE_API_TOKEN:
            return self.JUDGE_API_TOKEN
        cfg = self.get_model_config(self.JUDGE_MODEL_NAME)
        return cfg["token"]

    @property
    def embedding_endpoint(self) -> str:
        """Resolve embedding endpoint. Falls back to Model A endpoint."""
        if self.EMBEDDING_ENDPOINT:
            return self.EMBEDDING_ENDPOINT
        return self.MAAS_ENDPOINT_A

    @property
    def embedding_token(self) -> str:
        """Resolve embedding token. Falls back to Model A token."""
        if self.EMBEDDING_API_TOKEN:
            return self.EMBEDDING_API_TOKEN
        return self.MODEL_A_API_TOKEN

    @property
    def any_token_configured(self) -> bool:
        """Return True if at least one API token is configured."""
        return bool(self.MODEL_A_API_TOKEN or self.MODEL_B_API_TOKEN)

    @model_validator(mode="after")
    def validate_api_tokens(self) -> Self:
        """Warn if no API tokens are set."""
        if not self.MODEL_A_API_TOKEN and not self.MODEL_B_API_TOKEN:
            logger.warning(
                "No API tokens set. Set MODEL_A_API_TOKEN and MODEL_B_API_TOKEN "
                "to enable model serving."
            )
        return self


settings = Settings()
