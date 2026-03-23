# This project was developed with assistance from AI tools.
"""Pydantic schemas for model serving endpoints."""

from pydantic import BaseModel


class ModelResponse(BaseModel):
    """Response schema for a model configuration."""

    id: int
    name: str
    endpoint_url: str
    deployment_mode: str
    is_active: bool

    model_config = {"from_attributes": True}


class ModelStatusResponse(BaseModel):
    """Response for model health/status check."""

    name: str
    status: str
    deployment_mode: str
    endpoint_url: str
