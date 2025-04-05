import hashlib
import logging
import time

from django.conf import settings
from django.core.cache import cache

from common.ollama import get_ollama_client

logger = logging.getLogger(__name__)


def _embedding_cache_key(namespace: str, cleaned_text: str) -> str:
    """Build a checkpoint cache key from the model, namespace, and content hash."""
    digest = hashlib.sha256(f"{settings.OLLAMA_EMBEDDING_MODEL}:{cleaned_text}".encode()).hexdigest()
    return f"emb:{namespace}:{digest}"


def generate_embeddings(
    texts: list[str],
    cache_namespace: str | None = None,
) -> list[list[float]]:
    """Embed ``texts``, optionally checkpointing each vector in the cache.

    When ``cache_namespace`` is given, every embedding is written to (and read
    back from) the Django cache keyed by model + namespace + content hash. A
    retried ingest therefore resumes from the last successfully embedded chunk
    instead of re-embedding the whole document from scratch — the expensive,
    network-bound step is the one we checkpoint.
    """
    if not texts:
        return []

    results: list[list[float] | None] = [None] * len(texts)
    pending: list[tuple[int, str]] = []  # (original index, cleaned text)

    for i, text in enumerate(texts):
        cleaned = text.replace("\n", " ").strip()
        if cache_namespace is not None:
            cached = cache.get(_embedding_cache_key(cache_namespace, cleaned))
            if cached is not None:
                results[i] = cached
                continue
        pending.append((i, cleaned))

    if pending:
        client = get_ollama_client()
        batch_size = settings.EMBEDDING_BATCH_SIZE
        resumed = len(texts) - len(pending)

        for b in range(0, len(pending), batch_size):
            batch = pending[b : b + batch_size]
            response = client.embeddings.create(
                model=settings.OLLAMA_EMBEDDING_MODEL,
                input=[cleaned for _, cleaned in batch],
            )
            if len(response.data) != len(batch):
                raise ValueError(
                    f"Embedding API returned {len(response.data)} vectors for batch of {len(batch)}"
                )
            for (idx, cleaned), item in zip(batch, response.data, strict=True):
                results[idx] = item.embedding
                if cache_namespace is not None:
                    cache.set(
                        _embedding_cache_key(cache_namespace, cleaned),
                        item.embedding,
                        timeout=settings.EMBEDDING_CHECKPOINT_TTL,
                    )

            logger.debug(
                "Embeddings generated",
                extra={
                    "batch": b // batch_size + 1,
                    "count": len(batch),
                    "resumed_from_checkpoint": resumed,
                },
            )

            if b + batch_size < len(pending):
                time.sleep(0.1)

    return [r for r in results if r is not None]


def generate_query_embedding(text: str) -> list[float]:
    """Embed a single search query, caching the vector to skip repeat calls."""
    cleaned = text.replace("\n", " ").strip()
    cache_key = "qemb:" + hashlib.sha256(f"{settings.OLLAMA_EMBEDDING_MODEL}:{cleaned}".encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    response = get_ollama_client().embeddings.create(
        model=settings.OLLAMA_EMBEDDING_MODEL,
        input=cleaned,
    )
    embedding = response.data[0].embedding
    cache.set(cache_key, embedding, timeout=settings.QUERY_EMBEDDING_CACHE_TTL)
    return embedding
