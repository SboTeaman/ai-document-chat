from django.urls import path

from . import views

urlpatterns = [
    path(
        "workspaces/<int:workspace_id>/chat/sessions/", views.ChatSessionListCreateView.as_view(), name="chat-sessions"
    ),
    path(
        "workspaces/<int:workspace_id>/chat/sessions/<int:session_id>/",
        views.ChatSessionDetailView.as_view(),
        name="chat-session-detail",
    ),
    path(
        "workspaces/<int:workspace_id>/chat/sessions/<int:session_id>/messages/",
        views.SendMessageView.as_view(),
        name="chat-send-message",
    ),
]
