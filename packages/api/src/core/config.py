# This project was developed with assistance from AI tools.
"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "openshift-ai-model-evaluation"
    DEBUG: bool = False

    # CORS
    ALLOWED_HOSTS: list[str] = ["http://localhost:5173"]

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://user:password@localhost:5432/model-evaluation"
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

    model_config = {"env_file": ".env"}


settings = Settings()
