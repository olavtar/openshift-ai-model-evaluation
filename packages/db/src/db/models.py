# This project was developed with assistance from AI tools.

"""Database models for model evaluation."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from .database import Base

EMBEDDING_DIMENSION = 768


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


class Document(Base):
    """An uploaded document in the RAG knowledge base."""

    __tablename__ = "document"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(500), nullable=False)
    status = Column(String(50), nullable=False, default="processing")
    chunk_count = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class Chunk(Base):
    """A text chunk extracted from a document, with optional embedding."""

    __tablename__ = "chunk"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("document.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    source_document = Column(String(500), nullable=False)
    page_number = Column(String(20), nullable=True)
    section_path = Column(Text, nullable=True)
    element_type = Column(String(50), nullable=False, default="paragraph")
    token_count = Column(Integer, nullable=False, default=0)
    embedding = Column(Vector(EMBEDDING_DIMENSION), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
