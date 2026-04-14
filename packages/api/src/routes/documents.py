# This project was developed with assistance from AI tools.
"""Document management endpoints -- upload, list, and status."""

import logging
import os
from datetime import UTC, datetime

from db import Chunk, Document, get_db
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.documents import (
    DocumentResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from ..services.document_parser import parse_pdf
from ..services.embedding import generate_embeddings

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile,
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a PDF document for processing.

    Extracts text from each page and stores as chunks for later
    embedding and retrieval.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid content type")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")

    # Validate PDF magic bytes
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")

    # Sanitize filename
    safe_filename = os.path.basename(file.filename).replace("..", "")

    doc = Document(
        filename=safe_filename,
        status="processing",
        file_size_bytes=len(content),
    )
    session.add(doc)
    await session.flush()

    try:
        parse_result = parse_pdf(content, safe_filename)
    except Exception as e:
        logger.error("Failed to parse %s: %s", file.filename, e)
        doc.status = "error"
        doc.error_message = f"PDF parsing failed: {e}"
        doc_id = doc.id
        doc_filename = doc.filename
        error_msg = doc.error_message
        await session.commit()
        return DocumentUploadResponse(
            document_id=doc_id,
            filename=doc_filename,
            status="error",
            message=error_msg,
        )

    # Generate embeddings (returns None if unavailable)
    chunk_texts = [c.text for c in parse_result.chunks]
    embed_out = await generate_embeddings(chunk_texts)
    embeddings = embed_out.vectors

    db_chunks = []
    for i, chunk_data in enumerate(parse_result.chunks):
        chunk = Chunk(
            document_id=doc.id,
            text=chunk_data.text,
            source_document=chunk_data.source_document,
            page_number=chunk_data.page_number,
            section_path=chunk_data.section_path,
            element_type=chunk_data.element_type,
            token_count=chunk_data.token_count,
            embedding=embeddings[i] if embeddings else None,
        )
        db_chunks.append(chunk)

    session.add_all(db_chunks)
    doc.status = "ready"
    doc.chunk_count = len(db_chunks)
    doc.page_count = parse_result.page_count

    # Capture values before commit (commit expires ORM attributes in async context)
    doc_id = doc.id
    doc_filename = doc.filename
    num_chunks = len(db_chunks)
    num_pages = parse_result.page_count
    parser = parse_result.parser_used
    await session.commit()

    embed_status = "with embeddings" if embeddings else "without embeddings"
    return DocumentUploadResponse(
        document_id=doc_id,
        filename=doc_filename,
        status="ready",
        message=f"Extracted {num_chunks} chunks from {num_pages} pages ({embed_status}, parser: {parser})",
        embedding_error=embed_out.error,
    )


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    session: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List all non-deleted documents."""
    result = await session.execute(
        select(Document)
        .where(Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            status=doc.status,
            chunk_count=doc.chunk_count,
            page_count=doc.page_count,
            file_size_bytes=doc.file_size_bytes,
            error_message=doc.error_message,
            created_at=doc.created_at.isoformat() if doc.created_at else None,
        )
        for doc in docs
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get a single document by ID."""
    doc = await session.get(Document, document_id)
    if not doc or doc.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        chunk_count=doc.chunk_count,
        page_count=doc.page_count,
        file_size_bytes=doc.file_size_bytes,
        error_message=doc.error_message,
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a document (idempotent)."""
    doc = await session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.deleted_at is None:
        doc.deleted_at = datetime.now(UTC).replace(tzinfo=None)
        await session.commit()


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: int,
    session: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    """Get processing status for a document."""
    doc = await session.get(Document, document_id)
    if not doc or doc.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(
        document_id=doc.id,
        filename=doc.filename,
        status=doc.status,
        chunk_count=doc.chunk_count,
        page_count=doc.page_count,
        error_message=doc.error_message,
    )
