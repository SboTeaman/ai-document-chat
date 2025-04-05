from django.db import migrations
import pgvector.django.indexes
import pgvector.django.vector


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        # Drop HNSW index before altering column type
        migrations.RunSQL(
            sql="DROP INDEX IF EXISTS document_chunks_embedding_hnsw;",
            reverse_sql="",
        ),
        # Change vector dimension from 1536 to 768
        migrations.RunSQL(
            sql="ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768);",
            reverse_sql="ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536);",
        ),
        # Clear existing embeddings — they were generated with a different model
        migrations.RunSQL(
            sql="UPDATE document_chunks SET embedding = NULL;",
            reverse_sql="",
        ),
        # Reset document status so they get re-processed
        migrations.RunSQL(
            sql="UPDATE documents SET status = 'queued', chunk_count = 0 WHERE status = 'ready';",
            reverse_sql="",
        ),
        # Recreate HNSW index for new dimension
        migrations.AddIndex(
            model_name='documentchunk',
            index=pgvector.django.indexes.HnswIndex(
                ef_construction=64,
                fields=['embedding'],
                m=16,
                name='document_chunks_embedding_hnsw',
                opclasses=['vector_cosine_ops'],
            ),
        ),
        # Update Django migration state for the field
        migrations.AlterField(
            model_name='documentchunk',
            name='embedding',
            field=pgvector.django.vector.VectorField(dimensions=768, null=True),
        ),
    ]
