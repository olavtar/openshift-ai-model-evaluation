# This project was developed with assistance from AI tools.

"""Database models for model evaluation."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from .database import Base


class ModelConfig(Base):
    """Configuration for a served model available for evaluation."""

    __tablename__ = "model_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    endpoint_url = Column(String(500), nullable=False)
    deployment_mode = Column(String(50), nullable=False, default="maas")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ModelConfig(id={self.id}, name='{self.name}', mode='{self.deployment_mode}')>"
