from django.contrib import admin

from .models import Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["filename", "workspace", "status", "chunk_count", "file_size_bytes", "created_at"]
    list_filter = ["status", "mime_type"]
    search_fields = ["filename", "workspace__name"]
    readonly_fields = ["s3_key", "processing_started_at", "processing_finished_at", "error_message"]


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ["document", "chunk_index", "token_count"]
    search_fields = ["document__filename"]
    readonly_fields = ["embedding"]
