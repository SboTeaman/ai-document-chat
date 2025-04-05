from django.conf import settings
from django.db import models


class SearchQuery(models.Model):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="search_queries",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="search_queries",
    )
    query = models.TextField()
    result_count = models.PositiveSmallIntegerField(default=0)
    collection = models.ForeignKey(
        "collections.Collection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_queries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_queries"
        indexes = [models.Index(fields=["workspace_id", "created_at"])]

    def __str__(self):
        return f"{self.query[:50]} ({self.result_count} results)"
