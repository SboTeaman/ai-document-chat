from rest_framework.pagination import CursorPagination as BaseCursorPagination
from rest_framework.response import Response


class CursorPagination(BaseCursorPagination):
    """Default opaque-cursor pagination (20/page, newest first) returning the
    project's ``{data, pagination}`` envelope."""

    page_size = 20
    ordering = "-created_at"
    cursor_query_param = "cursor"

    def get_paginated_response(self, data):
        """Wrap the page rows together with next/previous cursor links."""
        return Response(
            {
                "data": data,
                "pagination": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
            }
        )


class ChatSessionPagination(CursorPagination):
    """Chat sessions ordered by most recent activity."""

    ordering = "-last_activity_at"


class WorkspacePagination(CursorPagination):
    """Workspaces, 50 per page (a user belongs to relatively few)."""

    page_size = 50
    ordering = "-created_at"


class MemberPagination(CursorPagination):
    """Workspace members, 100 per page, ordered by stable insertion id."""

    page_size = 100
    ordering = "id"
