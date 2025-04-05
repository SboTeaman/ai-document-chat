from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_alter_embedding_dimension'),
    ]

    operations = [
        # Guarantee one row per (document, chunk_index). The ingest pipeline
        # deletes-then-reinserts chunks, so a crash mid-write could otherwise
        # leave duplicate indices; the constraint makes that impossible.
        migrations.AddConstraint(
            model_name='documentchunk',
            constraint=models.UniqueConstraint(
                fields=['document', 'chunk_index'],
                name='uq_document_chunk_index',
            ),
        ),
        # Functional GIN index backing the FTS half of hybrid search.
        #
        # The language literal MUST match settings.SEARCH_FTS_LANGUAGE (default
        # 'english'). to_tsvector(regconfig, text) is IMMUTABLE so it can back
        # an index; the two-argument to_tsvector(text, text) form that resolves
        # the config at runtime is only STABLE and cannot. Changing the search
        # language therefore requires a new migration that rebuilds this index.
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS document_chunks_content_fts "
                "ON document_chunks USING GIN (to_tsvector('english', content));"
            ),
            reverse_sql="DROP INDEX IF EXISTS document_chunks_content_fts;",
        ),
    ]
