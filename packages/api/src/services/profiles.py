# This project was developed with assistance from AI tools.
"""Evaluation profile loader -- reads versioned YAML profiles from disk."""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"


class RetrievalConfig(BaseModel):
    """Retrieval parameters driven by the evaluation profile."""

    top_k: int = 10
    max_chunks_per_document: int = 4
    rerank_depth: int = 20
    document_diversity_min: int = 3
    keyword_search_enabled: bool = True


class EvalProfile(BaseModel):
    """An evaluation profile defining thresholds and retrieval config."""

    id: str
    version: str = "1.0"
    domain: str = ""
    description: str = ""
    answer_contract: list[str] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)
    critical_thresholds: dict[str, float] = Field(default_factory=dict)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)


def load_profile(profile_id: str) -> EvalProfile:
    """Load an evaluation profile by ID from the profiles directory.

    Args:
        profile_id: The profile filename stem (e.g., 'fsi_compliance_v1').

    Returns:
        Parsed EvalProfile.

    Raises:
        FileNotFoundError: If the profile YAML does not exist.
        ValueError: If the YAML is malformed or fails validation.
    """
    path = _PROFILES_DIR / f"{profile_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile '{profile_id}' not found at {path}")

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        return EvalProfile(**data)
    except Exception as e:
        raise ValueError(f"Failed to load profile '{profile_id}': {e}") from e


def list_profiles() -> list[str]:
    """Return available profile IDs (filename stems from profiles directory)."""
    if not _PROFILES_DIR.exists():
        return []
    return sorted(p.stem for p in _PROFILES_DIR.glob("*.yaml"))
