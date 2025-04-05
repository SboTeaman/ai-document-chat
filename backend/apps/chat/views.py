import logging

from django.db.models import Count
from django.http import StreamingHttpResponse
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import ChatSessionPagination
from common.permissions import IsWorkspaceMember

from .models import ChatMessage, ChatSession
from .serializers import ChatMessageSerializer, ChatSessionSerializer, SendMessageSerializer
from .services import stream_rag_response

logger = logging.getLogger(__name__)


class ChatSessionListCreateView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, workspace_id):
        """List the caller's chat sessions in this workspace (newest activity first)."""
        # Annotated count avoids an N+1 in the serializer.
        sessions = ChatSession.objects.filter(workspace_id=workspace_id, user=request.user).annotate(
            message_count_annotated=Count("messages")
        )
        paginator = ChatSessionPagination()
        page = paginator.paginate_queryset(sessions, request)
        return paginator.get_paginated_response(ChatSessionSerializer(page, many=True).data)

    def post(self, request, workspace_id):
        """Create a new (empty, untitled) chat session for the caller."""
        session = ChatSession.objects.create(
            workspace_id=workspace_id,
            user=request.user,
        )
        return Response({"data": ChatSessionSerializer(session).data}, status=status.HTTP_201_CREATED)


class ChatSessionDetailView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, workspace_id, session_id):
        session = self._get_session(workspace_id, session_id, request.user)
        messages = session.messages.all()
        return Response(
            {
                "data": {
                    "session": ChatSessionSerializer(session).data,
                    "messages": ChatMessageSerializer(messages, many=True).data,
                }
            }
        )

    def delete(self, request, workspace_id, session_id):
        session = self._get_session(workspace_id, session_id, request.user)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_session(self, workspace_id, session_id, user):
        """Fetch a session owned by the caller in this workspace, or raise 404."""
        try:
            return ChatSession.objects.get(workspace_id=workspace_id, id=session_id, user=user)
        except ChatSession.DoesNotExist:
            raise NotFound() from None


class SendMessageView(APIView):
    permission_classes = [IsWorkspaceMember]

    @ratelimit(key="user", rate="20/m", method="POST", block=True)
    def post(self, request, workspace_id, session_id):
        """Persist the user's message and stream the RAG answer back as SSE."""
        try:
            session = ChatSession.objects.get(workspace_id=workspace_id, id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            raise NotFound() from None

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["content"]
        collection_id = serializer.validated_data.get("collection_id")

        user_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=query,
        )

        if not session.title:
            session.title = query[:100]
            session.save(update_fields=["title"])

        history = list(
            session.messages.exclude(id=user_message.id).order_by("-created_at")[:10].values("role", "content")
        )
        history.reverse()

        def event_stream():
            """Relay SSE events from the RAG generator, persisting the reply at the end."""
            import json

            full_response = ""
            citations = []
            had_error = False
            completed = False

            def persist():
                """Save the streamed assistant reply when the stream ends."""
                # Persist whatever was streamed so far. Invoked exactly once from
                # the generator's finally block, so it fires even when the client
                # disconnects mid-stream (GeneratorExit) — otherwise the
                # assistant's reply would be lost and the session would show a
                # dangling user message.
                # Skip a truly empty answer that never started (e.g. immediate
                # disconnect), but keep partial text and normal empty completions.
                if not (full_response or (completed and not had_error)):
                    return
                ChatMessage.objects.create(
                    session=session,
                    role=ChatMessage.Role.ASSISTANT,
                    content=full_response,
                    citations=citations,
                )

            generator = stream_rag_response(
                query=query,
                workspace_id=workspace_id,
                session_messages=history,
                collection_id=collection_id,
            )
            try:
                for event in generator:
                    if isinstance(event, str) and event.startswith("data: "):
                        try:
                            data = json.loads(event[6:].strip())
                            if data.get("type") == "token":
                                full_response += data.get("token", "")
                            elif data.get("type") == "done":
                                citations = data.get("citations", [])
                            elif data.get("type") == "error":
                                had_error = True
                        except (json.JSONDecodeError, KeyError):
                            pass
                    yield event
                completed = True
            finally:
                persist()

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
