from rest_framework import serializers

from apps.collections.models import Collection

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)
    uploaded_by = serializers.SerializerMethodField()
    collection_name = serializers.CharField(source="collection.name", read_only=True)
    collection = serializers.SerializerMethodField()
    file_size_kb = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "filename",
            "mime_type",
            "file_size_bytes",
            "file_size_kb",
            "status",
            "error_message",
            "chunk_count",
            "collection",
            "collection_name",
            "uploaded_by",
            "uploaded_by_email",
            "processing_started_at",
            "processing_finished_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_size_kb(self, obj):
        return round(obj.file_size_bytes / 1024, 1)

    def get_collection(self, obj):
        """Nested {id, name} of the collection, or None if unfiled."""
        if obj.collection_id is None:
            return None
        return {"id": obj.collection_id, "name": obj.collection.name if obj.collection else None}

    def get_uploaded_by(self, obj):
        """Nested {id, email} of the uploader, or None if the user was removed."""
        if obj.uploaded_by_id is None:
            return None
        return {"id": obj.uploaded_by_id, "email": obj.uploaded_by.email if obj.uploaded_by else None}


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    collection_id = serializers.IntegerField(required=False, allow_null=True)

    def __init__(self, *args, workspace_id: int | None = None, **kwargs):
        """Capture the workspace id so collection ownership can be validated."""
        self._workspace_id = workspace_id
        super().__init__(*args, **kwargs)

    def validate_collection_id(self, value):
        """Ensure any given collection belongs to this workspace (anti-IDOR)."""
        if value is None:
            return value
        if self._workspace_id is None:
            raise serializers.ValidationError("Workspace context missing.")
        # Prevents cross-workspace IDOR: a member of workspace A cannot
        # attach a document to a collection that lives in workspace B.
        if not Collection.objects.filter(id=value, workspace_id=self._workspace_id).exists():
            raise serializers.ValidationError("Collection not found in this workspace.")
        return value
