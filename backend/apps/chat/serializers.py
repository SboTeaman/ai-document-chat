from rest_framework import serializers

from .models import ChatMessage, ChatSession


class ChatSessionSerializer(serializers.ModelSerializer):
    # Resolved either from an annotated queryset (preferred, no N+1) or, as a
    # fallback for detail views, by counting on the related manager.
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ["id", "title", "message_count", "last_activity_at", "created_at"]
        read_only_fields = fields

    def get_message_count(self, obj):
        """Message count: prefer the annotated value, else fall back to a query."""
        annotated = getattr(obj, "message_count_annotated", None)
        if annotated is not None:
            return annotated
        return obj.messages.count()


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "citations", "created_at"]
        read_only_fields = fields


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=5000)
    collection_id = serializers.IntegerField(required=False, allow_null=True)
