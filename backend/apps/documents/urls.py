from django.urls import path

from . import views

urlpatterns = [
    path("", views.DocumentListCreateView.as_view(), name="document-list"),
    path("<int:document_id>/", views.DocumentDetailView.as_view(), name="document-detail"),
    path("<int:document_id>/download/", views.DocumentDownloadView.as_view(), name="document-download"),
]
