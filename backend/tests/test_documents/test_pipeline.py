from unittest.mock import patch

import pytest

from apps.documents.models import Document, DocumentChunk
from apps.documents.tasks.chunking import chunk_text
from apps.documents.tasks.extraction import extract_text
from tests.factories import DocumentFactory


@pytest.mark.django_db
class TestChunking:
    def test_basic_chunking(self):
        text = "word " * 600
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) > 1
        assert all(c.token_count <= 100 for c in chunks)
        assert all(c.content.strip() for c in chunks)

    def test_chunk_indices_sequential(self):
        text = "word " * 300
        chunks = chunk_text(text, chunk_size=50, overlap=5)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_empty_text_returns_empty(self):
        chunks = chunk_text("", chunk_size=512, overlap=64)
        assert chunks == []

    def test_short_text_single_chunk(self):
        text = "This is a short document."
        chunks = chunk_text(text, chunk_size=512, overlap=64)
        assert len(chunks) == 1
        assert "short document" in chunks[0].content

    def test_overlap_produces_continuity(self):
        text = "word " * 200
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        assert len(chunks) >= 2


class TestExtraction:
    def test_plain_text_extraction(self):
        content = b"Hello world. This is a test."
        result = extract_text(content, "text/plain")
        assert "Hello world" in result

    def test_markdown_extraction(self):
        content = b"# Header\n\nThis is markdown."
        result = extract_text(content, "text/markdown")
        assert "Header" in result

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported MIME type"):
            extract_text(b"data", "image/png")


@pytest.mark.django_db
class TestIngestTask:
    def test_ingest_marks_ready_on_success(self, db):
        from apps.documents.tasks.ingest import ingest_document

        document = DocumentFactory(status=Document.Status.QUEUED)

        from apps.documents.tasks.chunking import Chunk

        fake_chunks = [Chunk(content="hello", chunk_index=i, token_count=5) for i in range(3)]

        with (
            patch("apps.documents.tasks.ingest._download_file", return_value=b"Hello world " * 50),
            patch("apps.documents.tasks.ingest.extract_text", return_value="Hello world content " * 50),
            patch("apps.documents.tasks.ingest.chunk_text", return_value=fake_chunks),
            patch("apps.documents.tasks.ingest.generate_embeddings", return_value=[[0.1] * 768] * 3),
        ):
            ingest_document(document.id)

        document.refresh_from_db()
        assert document.status == Document.Status.READY
        assert document.chunk_count > 0

    def test_ingest_marks_failed_after_max_retries(self, db):
        from apps.documents.tasks.ingest import ingest_document

        document = DocumentFactory(status=Document.Status.QUEUED)

        with patch("apps.documents.tasks.ingest._download_file", side_effect=Exception("S3 error")):
            ingest_document.apply(args=[document.id], retries=3)

        document.refresh_from_db()
        assert document.status == Document.Status.FAILED
        assert "S3 error" in document.error_message

    def test_ingest_nonexistent_document_returns_error(self, db):
        from apps.documents.tasks.ingest import ingest_document

        result = ingest_document(999999)
        assert result["status"] == "error"

    def test_chunks_deleted_on_reprocessing(self, db):
        from apps.documents.tasks.chunking import Chunk
        from apps.documents.tasks.ingest import _save_chunks

        document = DocumentFactory(status=Document.Status.QUEUED)
        DocumentChunk.objects.create(document=document, chunk_index=0, content="old", token_count=5)

        chunks = [Chunk(content="new content", chunk_index=0, token_count=5)]
        _save_chunks(document, chunks, [[0.1] * 768])

        assert DocumentChunk.objects.filter(document=document).count() == 1
        assert DocumentChunk.objects.get(document=document).content == "new content"
