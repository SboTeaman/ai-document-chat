import io
import uuid
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.documents.models import Document
from apps.documents.tasks import embedding, extraction
from apps.documents.tasks.chunking import Chunk
from apps.documents.tasks.extraction import ExtractionError, _guard_docx_bomb, extract_text
from apps.documents.tasks.ingest import _download_file, _save_chunks, ingest_document
from tests.factories import DocumentFactory

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class _Item:
    def __init__(self, e):
        self.embedding = e


class _Resp:
    def __init__(self, data):
        self.data = data


def _fake_create(model, input):
    n = len(input) if isinstance(input, list) else 1
    return _Resp([_Item([0.1] * 768) for _ in range(n)])


@pytest.mark.django_db
class TestEmbedding:
    def test_empty_returns_empty(self):
        assert embedding.generate_embeddings([]) == []

    def test_generates_and_resumes_from_cache(self):
        ns = "test-" + uuid.uuid4().hex
        with patch.object(embedding, "get_ollama_client") as mc:
            mc.return_value.embeddings.create.side_effect = _fake_create
            out = embedding.generate_embeddings(["alpha", "beta"], cache_namespace=ns)
        assert len(out) == 2
        # Second pass: everything is checkpointed, so the client is never built.
        with patch.object(embedding, "get_ollama_client") as mc2:
            out2 = embedding.generate_embeddings(["alpha", "beta"], cache_namespace=ns)
            mc2.assert_not_called()
        assert out2 == out

    @override_settings(EMBEDDING_BATCH_SIZE=2)
    def test_batches_and_sleeps_between_them(self):
        ns = "test-" + uuid.uuid4().hex
        with (
            patch.object(embedding, "get_ollama_client") as mc,
            patch("apps.documents.tasks.embedding.time.sleep") as sleep,
        ):
            mc.return_value.embeddings.create.side_effect = _fake_create
            out = embedding.generate_embeddings(["a", "b", "c"], cache_namespace=ns)
        assert len(out) == 3
        sleep.assert_called()

    def test_query_embedding_caches(self):
        text = "query " + uuid.uuid4().hex
        with patch.object(embedding, "get_ollama_client") as mc:
            mc.return_value.embeddings.create.side_effect = _fake_create
            e1 = embedding.generate_query_embedding(text)
        with patch.object(embedding, "get_ollama_client") as mc2:
            e2 = embedding.generate_query_embedding(text)
            mc2.assert_not_called()
        assert e1 == e2


class TestExtractionBranches:
    def test_pdf_extraction_skips_empty_pages(self):
        page = MagicMock()
        page.extract_text.return_value = "Hello PDF"
        empty = MagicMock()
        empty.extract_text.return_value = None
        fake_pdf = MagicMock()
        fake_pdf.pages = [page, empty]
        with patch("pdfplumber.open") as po:
            po.return_value.__enter__.return_value = fake_pdf
            out = extract_text(b"%PDF-1.4", "application/pdf")
        assert "Hello PDF" in out

    def test_pdf_too_many_pages(self):
        fake_pdf = MagicMock()
        fake_pdf.pages = [MagicMock()] * 1001
        with patch("pdfplumber.open") as po:
            po.return_value.__enter__.return_value = fake_pdf
            with pytest.raises(ExtractionError, match="max allowed"):
                extract_text(b"%PDF-1.4", "application/pdf")

    def test_docx_extraction(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<xml/>")
        para = MagicMock()
        para.text = "Hello DOCX"
        blank = MagicMock()
        blank.text = "   "
        fake_doc = MagicMock()
        fake_doc.paragraphs = [para, blank]
        with patch("docx.Document", return_value=fake_doc):
            out = extract_text(buf.getvalue(), DOCX_MIME)
        assert out == "Hello DOCX"

    def test_docx_bad_zip(self):
        with pytest.raises(ExtractionError, match="not a valid archive"):
            _guard_docx_bomb(b"not a zip")

    def test_docx_zip_bomb_rejected(self):
        info = MagicMock()
        info.file_size = 300 * 1024 * 1024
        fake_zip = MagicMock()
        fake_zip.__enter__.return_value.infolist.return_value = [info]
        with patch("apps.documents.tasks.extraction.zipfile.ZipFile", return_value=fake_zip):
            with pytest.raises(ExtractionError, match="exceeds limit"):
                _guard_docx_bomb(b"PKfake")

    def test_extracted_text_exceeds_limit(self):
        big = b"x" * (extraction.MAX_EXTRACTED_TEXT_CHARS + 1)
        with pytest.raises(ExtractionError, match="maximum allowed size"):
            extract_text(big, "text/plain")


@pytest.mark.django_db
class TestIngestBranches:
    def _run(self, **patches):
        doc = DocumentFactory(status=Document.Status.QUEUED)
        defaults = {
            "apps.documents.tasks.ingest._download_file": b"some bytes",
            "apps.documents.tasks.ingest.extract_text": "real text content",
            "apps.documents.tasks.ingest.chunk_text": [Chunk(content="c", chunk_index=0, token_count=5)],
            "apps.documents.tasks.ingest.generate_embeddings": [[0.1] * 768],
        }
        defaults.update(patches)
        with (
            patch(
                "apps.documents.tasks.ingest._download_file",
                return_value=defaults["apps.documents.tasks.ingest._download_file"],
            ),
            patch(
                "apps.documents.tasks.ingest.extract_text",
                return_value=defaults["apps.documents.tasks.ingest.extract_text"],
            ),
            patch(
                "apps.documents.tasks.ingest.chunk_text",
                return_value=defaults["apps.documents.tasks.ingest.chunk_text"],
            ),
            patch(
                "apps.documents.tasks.ingest.generate_embeddings",
                return_value=defaults["apps.documents.tasks.ingest.generate_embeddings"],
            ),
        ):
            ingest_document(doc.id)
        doc.refresh_from_db()
        return doc

    def test_no_extractable_text(self):
        doc = self._run(**{"apps.documents.tasks.ingest.extract_text": "   "})
        assert doc.status == Document.Status.FAILED
        assert "no extractable text" in doc.error_message

    def test_no_chunks(self):
        doc = self._run(**{"apps.documents.tasks.ingest.chunk_text": []})
        assert doc.status == Document.Status.FAILED
        assert "no output" in doc.error_message

    @override_settings(MAX_CHUNKS_PER_DOCUMENT=1)
    def test_too_many_chunks(self):
        chunks = [Chunk(content="c", chunk_index=i, token_count=5) for i in range(2)]
        doc = self._run(**{"apps.documents.tasks.ingest.chunk_text": chunks})
        assert doc.status == Document.Status.FAILED
        assert "max allowed" in doc.error_message

    def test_retry_is_raised_while_budget_remains(self):
        # With retries left, the task asks Celery to retry (eager mode raises Retry).
        from celery.exceptions import Retry

        doc = DocumentFactory(status=Document.Status.QUEUED)
        with patch("apps.documents.tasks.ingest._download_file", side_effect=Exception("S3 down")):
            with pytest.raises(Retry):
                ingest_document.apply(args=[doc.id], throw=True)

    def test_download_file_helper(self):
        with patch("common.storage.download_file_bytes", return_value=b"data"):
            assert _download_file("key") == b"data"

    def test_save_chunks_count_mismatch(self):
        doc = DocumentFactory()
        with pytest.raises(ValueError, match="mismatch"):
            _save_chunks(doc, [Chunk(content="c", chunk_index=0, token_count=5)], [[0.1] * 768, [0.2] * 768])
