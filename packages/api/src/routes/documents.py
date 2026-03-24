# This project was developed with assistance from AI tools.
"""Document management endpoints -- upload, list, and status."""

import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import Chunk, Document, get_db

from ..schemas.documents import (
    DocumentResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _extract_text_from_pdf(content: bytes) -> list[dict]:
    """Extract text from a PDF file, returning a list of page dicts.

    Each dict has 'page_number' (1-based) and 'text'.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"page_number": i, "text": text.strip()})
    return pages


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

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")

    doc = Document(
        filename=file.filename,
        status="processing",
        file_size_bytes=len(content),
    )
    session.add(doc)
    await session.flush()

    try:
        pages = _extract_text_from_pdf(content)
    except Exception as e:
        logger.error("Failed to extract text from %s: %s", file.filename, e)
        doc.status = "error"
        doc.error_message = f"PDF extraction failed: {e}"
        await session.commit()
        return DocumentUploadResponse(
            document_id=doc.id,
            filename=doc.filename,
            status="error",
            message=doc.error_message,
        )

    chunks = []
    for page in pages:
        chunk = Chunk(
            document_id=doc.id,
            text=page["text"],
            source_document=file.filename,
            page_number=str(page["page_number"]),
            element_type="page",
            token_count=len(page["text"].split()),
        )
        chunks.append(chunk)

    session.add_all(chunks)
    doc.status = "ready"
    doc.chunk_count = len(chunks)
    doc.page_count = len(pages)
    await session.commit()

    return DocumentUploadResponse(
        document_id=doc.id,
        filename=doc.filename,
        status="ready",
        message=f"Extracted {len(chunks)} chunks from {len(pages)} pages",
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
    """Soft-delete a document."""
    doc = await session.get(Document, document_id)
    if not doc or doc.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.deleted_at = datetime.now(timezone.utc)
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
