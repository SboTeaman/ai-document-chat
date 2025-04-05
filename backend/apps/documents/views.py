import logging

from django.conf import settings
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import create_audit_log
from common.pagination import CursorPagination
from common.permissions import CanDeleteDocument, CanUploadDocuments, IsWorkspaceMember
from common.storage import get_presigned_url

from . import services
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer

logger = logging.getLogger(__name__)


class DocumentListCreateView(APIView):
    def get_permissions(self):
        """Member/Admin/Owner may upload; any member may list."""
        if self.request.method == "POST":
            return [CanUploadDocuments()]
        return [IsWorkspaceMember()]

    def get(self, request, workspace_id):
        """List documents, optionally filtered by collection_id and status."""
        qs = Document.objects.filter(workspace_id=workspace_id).select_related("collection", "uploaded_by")
        collection_id = request.query_params.get("collection_id")
        if collection_id:
            qs = qs.filter(collection_id=collection_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(DocumentSerializer(page, many=True).data)

    @ratelimit(key="user", rate="30/m", method="POST", block=True)
    def post(self, request, workspace_id):
        """Upload a document, trigger ingestion, and write an audit row."""
        serializer = DocumentUploadSerializer(data=request.data, workspace_id=workspace_id)
        serializer.is_valid(raise_exception=True)

        document = services.upload_document(
            file_obj=serializer.validated_data["file"],
            workspace_id=workspace_id,
            collection_id=serializer.validated_data.get("collection_id"),
            uploaded_by=request.user,
        )

        create_audit_log(
            workspace_id=workspace_id,
            user=request.user,
            action="document.upload",
            resource_type="document",
            resource_id=document.id,
            metadata={"filename": document.filename},
            request=request,
        )

        return Response({"data": DocumentSerializer(document).data}, status=status.HTTP_202_ACCEPTED)


class DocumentDetailView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, workspace_id, document_id):
        document = self._get_document(workspace_id, document_id)
        return Response({"data": DocumentSerializer(document).data})

    def delete(self, request, workspace_id, document_id):
        """Delete a document (Admin/Owner, or the uploader of their own)."""
        document = self._get_document(workspace_id, document_id)
        self.check_object_permissions(request, document)
        services.delete_document(document)
        create_audit_log(
            workspace_id=workspace_id,
            user=request.user,
            action="document.delete",
            resource_type="document",
            resource_id=document_id,
            metadata={"filename": document.filename},
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self):
        """Deletion uses object-level CanDeleteDocument; reads need membership."""
        if self.request.method == "DELETE":
            return [CanDeleteDocument()]
        return [IsWorkspaceMember()]

    def _get_document(self, workspace_id, document_id):
        """Fetch a document scoped to the workspace, or raise 404."""
        try:
            return Document.objects.select_related("collection", "uploaded_by").get(
                workspace_id=workspace_id, id=document_id
            )
        except Document.DoesNotExist:
            raise NotFound() from None


class DocumentDownloadView(APIView):
    """Return a short-lived presigned URL for the original file.

    The object key is never exposed; the URL expires after
    AWS_PRESIGNED_URL_EXPIRY (15 min). Access is scoped to workspace members.
    """

    permission_classes = [IsWorkspaceMember]

    def get(self, request, workspace_id, document_id):
        """Issue a time-limited presigned download URL for the document."""
        try:
            document = Document.objects.get(workspace_id=workspace_id, id=document_id)
        except Document.DoesNotExist:
            raise NotFound() from None
        url = get_presigned_url(document.s3_key)
        return Response({"data": {"url": url, "expires_in": settings.AWS_PRESIGNED_URL_EXPIRY}})
