from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.documents.models import Document
from apps.search.services import _fts_language, hybrid_search
from tests.factories import CollectionFactory, DocumentChunkFactory, DocumentFactory, WorkspaceFactory

MOCK_EMBEDDING = [0.1] * 768


class TestFtsLanguage:
    @override_settings(SEARCH_FTS_LANGUAGE="not a valid identifier!")
    def test_invalid_language_falls_back_to_english(self):
        assert _fts_language() == "english"

    @override_settings(SEARCH_FTS_LANGUAGE="simple")
    def test_valid_language_passes_through(self):
        assert _fts_language() == "simple"


@pytest.mark.django_db
class TestHybridSearchCollectionFilter:
    def test_collection_filter_applied(self):
        ws = WorkspaceFactory()
        col = CollectionFactory(workspace=ws)
        doc = DocumentFactory(workspace=ws, collection=col, status=Document.Status.READY)
        DocumentChunkFactory(document=doc, content="python backend service", embedding=MOCK_EMBEDDING)
        with patch("apps.search.services.generate_query_embedding", return_value=MOCK_EMBEDDING):
            results = hybrid_search("python", ws.id, collection_id=col.id, limit=5)
        assert all(r.document_id == doc.id for r in results)
