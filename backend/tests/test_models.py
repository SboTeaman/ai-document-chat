from types import SimpleNamespace

import pytest
from django.test import override_settings

from apps.authentication.models import AuditLog, create_audit_log
from tests.factories import (
    AuditLogFactory,
    ChatMessageFactory,
    ChatSessionFactory,
    CollectionFactory,
    DocumentChunkFactory,
    DocumentFactory,
    SearchQueryFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)


@pytest.mark.django_db
class TestStrMethods:
    def test_all_str_methods(self):
        assert str(UserFactory(email="a@b.com")) == "a@b.com"
        ws = WorkspaceFactory(name="WS")
        assert str(ws) == "WS"
        m = WorkspaceMemberFactory(workspace=ws)
        assert "in WS" in str(m)
        col = CollectionFactory(workspace=ws, name="Docs")
        assert str(col) == "WS / Docs"
        doc = DocumentFactory(filename="f.pdf")
        assert str(doc) == "f.pdf"
        chunk = DocumentChunkFactory(document=doc, chunk_index=3)
        assert "Chunk 3" in str(chunk)
        sess = ChatSessionFactory(user=UserFactory(email="u@b.com"))
        assert "u@b.com" in str(sess)
        msg = ChatMessageFactory(content="Hello there")
        assert str(msg).startswith("user: Hello")
        sq = SearchQueryFactory(query="find me", result_count=2)
        assert "find me" in str(sq) and "2 results" in str(sq)
        log = AuditLogFactory(action="document.upload")
        assert "document.upload" in str(log)


@pytest.mark.django_db
class TestAuditLog:
    def test_create_audit_log_without_request(self):
        ws = WorkspaceFactory()
        create_audit_log(workspace_id=ws.id, user=ws.owner, action="x", resource_type="t", resource_id=1)
        assert AuditLog.objects.filter(action="x").exists()

    def test_client_ip_uses_remote_addr_when_no_trusted_proxy(self):
        ws = WorkspaceFactory()
        req = SimpleNamespace(
            META={"REMOTE_ADDR": "5.5.5.5", "HTTP_X_FORWARDED_FOR": "1.1.1.1", "HTTP_USER_AGENT": "UA"}
        )
        create_audit_log(workspace_id=ws.id, user=ws.owner, action="a", resource_type="t", request=req)
        assert AuditLog.objects.get(action="a").ip_address == "5.5.5.5"

    @override_settings(TRUSTED_PROXY_IPS=["10.0.0.1"])
    def test_client_ip_honours_xff_from_trusted_proxy(self):
        ws = WorkspaceFactory()
        req = SimpleNamespace(
            META={"REMOTE_ADDR": "10.0.0.1", "HTTP_X_FORWARDED_FOR": "8.8.8.8, 10.0.0.1", "HTTP_USER_AGENT": "UA"}
        )
        create_audit_log(workspace_id=ws.id, user=ws.owner, action="b", resource_type="t", request=req)
        assert AuditLog.objects.get(action="b").ip_address == "8.8.8.8"

    @override_settings(TRUSTED_PROXY_IPS=["10.0.0.1"])
    def test_client_ip_trusted_proxy_without_xff(self):
        ws = WorkspaceFactory()
        req = SimpleNamespace(META={"REMOTE_ADDR": "10.0.0.1", "HTTP_USER_AGENT": "UA"})
        create_audit_log(workspace_id=ws.id, user=ws.owner, action="c", resource_type="t", request=req)
        assert AuditLog.objects.get(action="c").ip_address == "10.0.0.1"
