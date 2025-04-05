import logging

from django_ratelimit.decorators import ratelimit
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsWorkspaceMember

from .models import SearchQuery
from .serializers import SearchRequestSerializer, SearchResultSerializer
from .services import hybrid_search

logger = logging.getLogger(__name__)


class SearchView(APIView):
    permission_classes = [IsWorkspaceMember]

    @ratelimit(key="user", rate="30/m", method="POST", block=True)
    def post(self, request, workspace_id):
        """Run a hybrid (vector + FTS) search and log the query for analytics."""
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        collection_id = serializer.validated_data.get("collection_id")
        limit = serializer.validated_data["limit"]

        results = hybrid_search(
            query=query,
            workspace_id=workspace_id,
            collection_id=collection_id,
            limit=limit,
        )

        SearchQuery.objects.create(
            workspace_id=workspace_id,
            user=request.user,
            query=query,
            result_count=len(results),
            collection_id=collection_id,  # ForeignKey — accepts raw PK
        )

        return Response(
            {
                "data": SearchResultSerializer(results, many=True).data,
                "meta": {"total": len(results), "query": query},
            }
        )
