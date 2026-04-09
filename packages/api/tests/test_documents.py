# This project was developed with assistance from AI tools.
"""Tests for document management endpoints (/documents)."""

import io
from unittest.mock import AsyncMock, patch

from src.services.embedding import EmbeddingsResult

# --- Helpers ---


def _make_pdf_bytes() -> bytes:
    """Create a minimal valid PDF file."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _mock_extract(pages: list[dict]):
    """Return a patch that replaces _extract_text_from_pdf."""
    return patch(
        "src.routes.documents._extract_text_from_pdf",
        return_value=pages,
    )


def _mock_no_embeddings():
    """Return a patch that skips embedding generation."""
    return patch(
        "src.routes.documents.generate_embeddings",
        new_callable=AsyncMock,
        return_value=EmbeddingsResult(vectors=None, error=None),
    )


# --- Upload tests ---


def test_upload_pdf_success(client):
    """Should upload a PDF and return document info with chunks."""
    pdf = _make_pdf_bytes()
    mock_pages = [
        {"page_number": 1, "text": "Page one content"},
        {"page_number": 2, "text": "Page two content"},
    ]
    with _mock_extract(mock_pages), _mock_no_embeddings():
        response = client.post(
            "/documents/upload",
            files={"file": ("test.pdf", pdf, "application/pdf")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ready"
    assert data["filename"] == "test.pdf"
    assert data["document_id"] >= 1
    assert "2 chunks" in data["message"]
    assert "without embeddings" in data["message"]


def test_upload_rejects_non_pdf(client):
    """Should return 400 when uploading a non-PDF file."""
    response = client.post(
        "/documents/upload",
        files={"file": ("readme.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_upload_handles_extraction_error(client):
    """Should return error status when PDF extraction fails."""
    pdf = _make_pdf_bytes()
    with patch(
        "src.routes.documents._extract_text_from_pdf",
        side_effect=Exception("corrupt pdf"),
    ), _mock_no_embeddings():
        response = client.post(
            "/documents/upload",
            files={"file": ("bad.pdf", pdf, "application/pdf")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "error"
    assert "corrupt pdf" in data["message"]


# --- List tests ---


def test_list_documents_empty(client):
    """Should return empty list when no documents exist."""
    response = client.get("/documents/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_documents_after_upload(client):
    """Should include uploaded document in list."""
    pdf = _make_pdf_bytes()
    with _mock_extract([{"page_number": 1, "text": "content"}]), _mock_no_embeddings():
        client.post(
            "/documents/upload",
            files={"file": ("doc.pdf", pdf, "application/pdf")},
        )

    response = client.get("/documents/")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 1
    assert docs[0]["filename"] == "doc.pdf"
    assert docs[0]["status"] == "ready"


# --- Get / Status / Delete tests ---


def test_get_document_by_id(client):
    """Should return a specific document by ID."""
    pdf = _make_pdf_bytes()
    with _mock_extract([{"page_number": 1, "text": "content"}]), _mock_no_embeddings():
        upload = client.post(
            "/documents/upload",
            files={"file": ("doc.pdf", pdf, "application/pdf")},
        )
    doc_id = upload.json()["document_id"]

    response = client.get(f"/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["filename"] == "doc.pdf"


def test_get_document_not_found(client):
    """Should return 404 for non-existent document."""
    response = client.get("/documents/999")
    assert response.status_code == 404


def test_document_status(client):
    """Should return processing status for a document."""
    pdf = _make_pdf_bytes()
    with _mock_extract([{"page_number": 1, "text": "content"}]), _mock_no_embeddings():
        upload = client.post(
            "/documents/upload",
            files={"file": ("doc.pdf", pdf, "application/pdf")},
        )
    doc_id = upload.json()["document_id"]

    response = client.get(f"/documents/{doc_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["chunk_count"] == 1


def test_delete_document(client):
    """Should soft-delete a document so it no longer appears in list."""
    pdf = _make_pdf_bytes()
    with _mock_extract([{"page_number": 1, "text": "content"}]), _mock_no_embeddings():
        upload = client.post(
            "/documents/upload",
            files={"file": ("doc.pdf", pdf, "application/pdf")},
        )
    doc_id = upload.json()["document_id"]

    response = client.delete(f"/documents/{doc_id}")
    assert response.status_code == 204

    # Should no longer appear in list
    response = client.get("/documents/")
    assert response.json() == []

    # Should return 404 on direct get
    response = client.get(f"/documents/{doc_id}")
    assert response.status_code == 404


def test_delete_document_not_found(client):
    """Should return 404 when deleting non-existent document."""
    response = client.delete("/documents/999")
    assert response.status_code == 404
