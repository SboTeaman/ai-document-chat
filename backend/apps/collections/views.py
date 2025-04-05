from django.db.models import Count
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.permissions import CanManageWorkspace, IsWorkspaceMember

from .models import Collection
from .serializers import CollectionCreateSerializer, CollectionSerializer


class CollectionListCreateView(APIView):
    def get_permissions(self):
        """Admin/Owner may create collections; any member may list them."""
        if self.request.method == "POST":
            return [CanManageWorkspace()]
        return [IsWorkspaceMember()]

    def get(self, request, workspace_id):
        """List the workspace's collections with their document counts."""
        collections = Collection.objects.filter(workspace_id=workspace_id).annotate(
            document_count_annotated=Count("documents")
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(collections, request)
        return paginator.get_paginated_response(CollectionSerializer(page, many=True).data)

    def post(self, request, workspace_id):
        """Create a collection in the workspace (Admin/Owner)."""
        serializer = CollectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        collection = serializer.save(workspace_id=workspace_id)
        return Response({"data": CollectionSerializer(collection).data}, status=status.HTTP_201_CREATED)


class CollectionDetailView(APIView):
    def get_permissions(self):
        """Admin/Owner may modify/delete; any member may read."""
        if self.request.method in ("PATCH", "PUT", "DELETE"):
            return [CanManageWorkspace()]
        return [IsWorkspaceMember()]

    def get(self, request, workspace_id, collection_id):
        collection = self._get_collection(workspace_id, collection_id)
        return Response({"data": CollectionSerializer(collection).data})

    def patch(self, request, workspace_id, collection_id):
        """Partially update a collection's name/description (Admin/Owner)."""
        collection = self._get_collection(workspace_id, collection_id)
        serializer = CollectionCreateSerializer(collection, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"data": CollectionSerializer(collection).data})

    def delete(self, request, workspace_id, collection_id):
        """Delete a collection (Admin/Owner). Documents are detached, not deleted."""
        collection = self._get_collection(workspace_id, collection_id)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_collection(self, workspace_id, collection_id):
        """Fetch a collection scoped to the workspace, or raise 404."""
        try:
            return Collection.objects.get(workspace_id=workspace_id, id=collection_id)
        except Collection.DoesNotExist:
            raise NotFound() from None
