from rest_framework import serializers

from .models import Collection


class CollectionSerializer(serializers.ModelSerializer):
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = ["id", "name", "description", "document_count", "created_at"]
        read_only_fields = ["id", "document_count", "created_at"]

    def get_document_count(self, obj):
        """Document count: prefer the annotated value, else fall back to a query."""
        annotated = getattr(obj, "document_count_annotated", None)
        if annotated is not None:
            return annotated
        return obj.documents.count()


class CollectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ["name", "description"]
