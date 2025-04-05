from rest_framework import serializers


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1, max_length=1000)
    collection_id = serializers.IntegerField(required=False, allow_null=True)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=10)


class SearchResultSerializer(serializers.Serializer):
    chunk_id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    document_name = serializers.CharField()
    content = serializers.CharField()
    chunk_index = serializers.IntegerField()
    similarity_score = serializers.FloatField()
