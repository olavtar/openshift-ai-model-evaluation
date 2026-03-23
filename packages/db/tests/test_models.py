# This project was developed with assistance from AI tools.

"""Model schema tests (no database required)."""

from db.models import ModelConfig


def test_model_config_table_name():
    """ModelConfig should map to model_config table."""
    assert ModelConfig.__tablename__ == "model_config"


def test_model_config_has_required_columns():
    """ModelConfig should have all expected columns."""
    columns = {c.name for c in ModelConfig.__table__.columns}
    expected = {"id", "name", "endpoint_url", "deployment_mode", "is_active", "created_at", "updated_at"}
    assert expected == columns


def test_model_config_name_is_unique():
    """Model name should be unique to prevent duplicate entries."""
    name_col = ModelConfig.__table__.c.name
    assert name_col.unique is True


def test_model_config_repr():
    """ModelConfig repr should show key fields."""
    m = ModelConfig(id=1, name="test-model", deployment_mode="maas")
    assert "test-model" in repr(m)
    assert "maas" in repr(m)
