from django.urls import path

from . import views

urlpatterns = [
    path("", views.CollectionListCreateView.as_view(), name="collection-list"),
    path("<int:collection_id>/", views.CollectionDetailView.as_view(), name="collection-detail"),
]
