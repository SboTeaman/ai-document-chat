from django.urls import path

from .views import SearchView

urlpatterns = [
    path("workspaces/<int:workspace_id>/search/", SearchView.as_view(), name="search"),
]
