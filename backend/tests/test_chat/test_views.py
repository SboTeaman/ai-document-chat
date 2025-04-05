from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.chat.models import ChatMessage, ChatSession
from tests.factories import ChatMessageFactory, ChatSessionFactory, WorkspaceMemberFactory


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.mark.django_db
class TestChatSessions:
    def test_create_and_list(self):
        m = WorkspaceMemberFactory()
        created = client_for(m.user).post(f"/api/workspaces/{m.workspace_id}/chat/sessions/")
        assert created.status_code == 201
        listed = client_for(m.user).get(f"/api/workspaces/{m.workspace_id}/chat/sessions/")
        assert listed.status_code == 200
        assert len(listed.json()["data"]) == 1

    def test_detail_returns_messages(self):
        m = WorkspaceMemberFactory()
        sess = ChatSessionFactory(workspace=m.workspace, user=m.user)
        ChatMessageFactory(session=sess, content="hi there")
        r = client_for(m.user).get(f"/api/workspaces/{m.workspace_id}/chat/sessions/{sess.id}/")
        assert r.status_code == 200
        assert r.json()["data"]["messages"][0]["content"] == "hi there"

    def test_delete_session(self):
        m = WorkspaceMemberFactory()
        sess = ChatSessionFactory(workspace=m.workspace, user=m.user)
        r = client_for(m.user).delete(f"/api/workspaces/{m.workspace_id}/chat/sessions/{sess.id}/")
        assert r.status_code == 204
        assert not ChatSession.objects.filter(id=sess.id).exists()

    def test_detail_not_found(self):
        m = WorkspaceMemberFactory()
        r = client_for(m.user).get(f"/api/workspaces/{m.workspace_id}/chat/sessions/999999/")
        assert r.status_code == 404


@pytest.mark.django_db
class TestSendMessage:
    def _stream_ok(self, **kwargs):
        yield 'data: {"type": "token", "token": "Hi"}\n\n'
        yield 'data: {"type": "done", "citations": []}\n\n'

    def _stream_error(self, **kwargs):
        yield 'data: {"type": "error", "message": "unavailable"}\n\n'

    def _stream_malformed(self, **kwargs):
        yield "data: {not valid json}\n\n"
        yield 'data: {"type": "done", "citations": []}\n\n'

    def test_streams_and_persists_assistant_message(self):
        m = WorkspaceMemberFactory()
        sess = ChatSessionFactory(workspace=m.workspace, user=m.user, title="")
        with patch("apps.chat.views.stream_rag_response", side_effect=self._stream_ok):
            r = client_for(m.user).post(
                f"/api/workspaces/{m.workspace_id}/chat/sessions/{sess.id}/messages/",
                {"content": "hello"},
            )
            body = b"".join(r.streaming_content).decode()
        assert r.status_code == 200
        assert "Hi" in body
        assert ChatMessage.objects.filter(session=sess, role="assistant", content="Hi").exists()
        sess.refresh_from_db()
        assert sess.title == "hello"

    def test_error_only_stream_does_not_persist_assistant(self):
        m = WorkspaceMemberFactory()
        sess = ChatSessionFactory(workspace=m.workspace, user=m.user)
        with patch("apps.chat.views.stream_rag_response", side_effect=self._stream_error):
            r = client_for(m.user).post(
                f"/api/workspaces/{m.workspace_id}/chat/sessions/{sess.id}/messages/",
                {"content": "hello"},
            )
            b"".join(r.streaming_content)
        assert not ChatMessage.objects.filter(session=sess, role="assistant").exists()

    def test_malformed_event_is_ignored(self):
        m = WorkspaceMemberFactory()
        sess = ChatSessionFactory(workspace=m.workspace, user=m.user)
        with patch("apps.chat.views.stream_rag_response", side_effect=self._stream_malformed):
            r = client_for(m.user).post(
                f"/api/workspaces/{m.workspace_id}/chat/sessions/{sess.id}/messages/",
                {"content": "hello"},
            )
            body = b"".join(r.streaming_content).decode()
        assert r.status_code == 200
        assert "{not valid json}" in body

    def test_session_not_found(self):
        m = WorkspaceMemberFactory()
        r = client_for(m.user).post(
            f"/api/workspaces/{m.workspace_id}/chat/sessions/999999/messages/",
            {"content": "hello"},
        )
        assert r.status_code == 404
