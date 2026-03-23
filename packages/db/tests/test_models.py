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


# --- Document model tests ---


def test_document_table_name():
    """Document should map to document table."""
    from db.models import Document

    assert Document.__tablename__ == "document"


def test_document_has_required_columns():
    """Document should have all expected columns."""
    from db.models import Document

    columns = {c.name for c in Document.__table__.columns}
    expected = {
        "id", "filename", "status", "chunk_count", "page_count",
        "file_size_bytes", "error_message", "created_at", "deleted_at",
    }
    assert expected == columns


def test_document_repr():
    """Document repr should show key fields."""
    from db.models import Document

    d = Document(id=1, filename="test.pdf", status="ready")
    assert "test.pdf" in repr(d)
    assert "ready" in repr(d)


# --- Chunk model tests ---


def test_chunk_table_name():
    """Chunk should map to chunk table."""
    from db.models import Chunk

    assert Chunk.__tablename__ == "chunk"


def test_chunk_has_required_columns():
    """Chunk should have all expected columns."""
    from db.models import Chunk

    columns = {c.name for c in Chunk.__table__.columns}
    expected = {
        "id", "document_id", "text", "source_document", "page_number",
        "section_path", "element_type", "token_count", "created_at",
    }
    assert expected == columns


def test_chunk_document_id_has_foreign_key():
    """Chunk.document_id should reference document.id."""
    from db.models import Chunk

    fk = list(Chunk.__table__.c.document_id.foreign_keys)
    assert len(fk) == 1
    assert str(fk[0].column) == "document.id"
