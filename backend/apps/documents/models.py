from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class Document(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    collection = models.ForeignKey(
        "collections.Collection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents",
    )
    filename = models.CharField(max_length=500)
    s3_key = models.CharField(max_length=1000)
    mime_type = models.CharField(max_length=100)
    file_size_bytes = models.PositiveBigIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    error_message = models.TextField(blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    processing_started_at = models.DateTimeField(null=True)
    processing_finished_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents"
        indexes = [
            models.Index(fields=["workspace_id", "status"]),
            models.Index(fields=["workspace_id", "collection_id"]),
            models.Index(fields=["workspace_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return self.filename


class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    token_count = models.PositiveIntegerField()
    embedding = VectorField(dimensions=768, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_chunks"
        ordering = ["chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="uq_document_chunk_index",
            ),
        ]
        indexes = [
            models.Index(fields=["document_id"]),
            HnswIndex(
                name="document_chunks_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"Chunk {self.chunk_index} of {self.document.filename}"
