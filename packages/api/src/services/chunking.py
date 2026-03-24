# This project was developed with assistance from AI tools.
"""Text chunking for RAG pipeline.

Splits page-level text into smaller, overlapping chunks suitable
for embedding and retrieval.
"""

CHUNK_SIZE = 512  # target tokens per chunk (approximated by words)
CHUNK_OVERLAP = 64  # overlap tokens between consecutive chunks


def chunk_text(
    text: str,
    source_document: str,
    page_number: str | None = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """Split text into overlapping chunks.

    Args:
        text: The source text to chunk.
        source_document: Filename for provenance tracking.
        page_number: Optional page number string.
        chunk_size: Target number of words per chunk.
        chunk_overlap: Number of overlapping words between chunks.

    Returns:
        List of chunk dicts with 'text', 'source_document',
        'page_number', 'token_count' keys.
    """
    words = text.split()
    if not words:
        return []

    # If text fits in a single chunk, return it as-is
    if len(words) <= chunk_size:
        return [
            {
                "text": text,
                "source_document": source_document,
                "page_number": page_number,
                "token_count": len(words),
            }
        ]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append(
            {
                "text": " ".join(chunk_words),
                "source_document": source_document,
                "page_number": page_number,
                "token_count": len(chunk_words),
            }
        )
        # Advance by (chunk_size - overlap), but at least 1 word
        step = max(chunk_size - chunk_overlap, 1)
        start += step

    return chunks
