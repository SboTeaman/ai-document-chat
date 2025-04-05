from django.urls import include, path

from . import views

workspace_urlpatterns = [
    path("", views.WorkspaceListCreateView.as_view(), name="workspace-list"),
    path("<int:workspace_id>/", views.WorkspaceDetailView.as_view(), name="workspace-detail"),
    path("<int:workspace_id>/members/", views.WorkspaceMembersView.as_view(), name="workspace-members"),
    path(
        "<int:workspace_id>/members/<int:member_id>/",
        views.WorkspaceMemberDetailView.as_view(),
        name="workspace-member-detail",
    ),
    path("<int:workspace_id>/collections/", include("apps.collections.urls")),
    path("<int:workspace_id>/documents/", include("apps.documents.urls")),
]

urlpatterns = workspace_urlpatterns
