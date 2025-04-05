import logging
import re
from dataclasses import dataclass

from django.conf import settings
from django.db import connection

from apps.documents.tasks.embedding import generate_query_embedding

logger = logging.getLogger(__name__)


def _fts_language() -> str:
    """Return a validated regconfig name for FTS.

    The value comes from settings (trusted), but it is interpolated as a SQL
    literal so the planner can match the functional GIN index — so we still
    guard against anything that is not a plain identifier.
    """
    lang = settings.SEARCH_FTS_LANGUAGE
    if not re.fullmatch(r"[a-z_]+", lang):
        logger.warning("Invalid SEARCH_FTS_LANGUAGE %r; falling back to 'english'", lang)
        return "english"
    return lang


@dataclass
class SearchResult:
    chunk_id: int
    document_id: int
    document_name: str
    content: str
    chunk_index: int
    similarity_score: float


def hybrid_search(
    query: str,
    workspace_id: int,
    collection_id: int | None = None,
    limit: int = 10,
    min_score: float | None = None,
) -> list[SearchResult]:
    """Run hybrid retrieval and return the top scored chunks.

    Combines vector similarity and full-text rank with weighted scoring
    (``vector_weight * cosine + fts_weight * normalised_fts``), filters by the
    minimum-score threshold, and returns at most ``limit`` results.
    """
    query_embedding = generate_query_embedding(query)
    raw = _run_hybrid_query(query, query_embedding, workspace_id, collection_id, limit * 3)

    if not raw:
        return []

    fts_max = max((r["fts_score"] for r in raw), default=0.0) or 1.0
    threshold = settings.SEARCH_MIN_SCORE if min_score is None else min_score
    v_w = settings.SEARCH_VECTOR_WEIGHT
    f_w = settings.SEARCH_FTS_WEIGHT

    scored = []
    for r in raw:
        fts_norm = (r["fts_score"] / fts_max) if fts_max else 0.0
        score = v_w * r["vector_score"] + f_w * fts_norm
        if score >= threshold:
            scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    scored = scored[:limit]

    results = [
        SearchResult(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            document_name=r["document_name"],
            content=r["content"],
            chunk_index=r["chunk_index"],
            similarity_score=round(float(s), 4),
        )
        for s, r in scored
    ]
    logger.debug(
        "Search complete",
        extra={"workspace_id": workspace_id, "results": len(results)},
    )
    return results


def _run_hybrid_query(
    query: str,
    query_embedding: list[float],
    workspace_id: int,
    collection_id: int | None,
    limit: int,
) -> list[dict]:
    """Execute the raw SQL that merges vector and FTS candidate sets.

    Both candidate sets are gathered independently and combined with a FULL
    OUTER JOIN so a strong keyword-only or vector-only match is not dropped.
    """
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    collection_filter = "AND d.collection_id = %(collection_id)s" if collection_id else ""
    lang = _fts_language()

    # SECURITY NOTE: `lang` and `collection_filter` are interpolated directly
    # into the SQL string via an f-string, which would be dangerous with
    # user-supplied input. `lang` is safe here because _fts_language() validates
    # it against the regex allowlist r"[a-z_]+" before returning it, ensuring
    # only plain lowercase identifiers can reach this point. `collection_filter`
    # is a hard-coded string constant, never derived from user input.
    # All actual user-supplied values (workspace_id, collection_id, query,
    # embedding) are passed as parameterised %(name)s placeholders below.
    # Both candidate sets are gathered independently and merged with a FULL OUTER
    # JOIN so a strong keyword (FTS-only) match is not dropped just because the
    # vector search missed it — and vice versa. The literal `lang` lets the
    # planner use the functional GIN index on to_tsvector(lang, content).
    sql = f"""
        WITH vector_scores AS (
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                dc.content,
                dc.chunk_index,
                1 - (dc.embedding <=> %(embedding)s::vector) AS vector_score
            FROM document_chunks dc
            INNER JOIN documents d ON d.id = dc.document_id
            WHERE d.workspace_id = %(workspace_id)s
              AND d.status = 'ready'
              AND dc.embedding IS NOT NULL
              {collection_filter}
            ORDER BY dc.embedding <=> %(embedding)s::vector
            LIMIT %(prelimit)s
        ),
        fts_scores AS (
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                dc.content,
                dc.chunk_index,
                ts_rank_cd(
                    to_tsvector('{lang}', dc.content),
                    plainto_tsquery('{lang}', %(query)s)
                ) AS fts_score
            FROM document_chunks dc
            INNER JOIN documents d ON d.id = dc.document_id
            WHERE d.workspace_id = %(workspace_id)s
              AND d.status = 'ready'
              AND to_tsvector('{lang}', dc.content) @@ plainto_tsquery('{lang}', %(query)s)
              {collection_filter}
            ORDER BY fts_score DESC
            LIMIT %(prelimit)s
        )
        SELECT
            COALESCE(vs.chunk_id, fs.chunk_id)       AS chunk_id,
            COALESCE(vs.document_id, fs.document_id)  AS document_id,
            d.filename                                AS document_name,
            COALESCE(vs.content, fs.content)          AS content,
            COALESCE(vs.chunk_index, fs.chunk_index)  AS chunk_index,
            COALESCE(vs.vector_score, 0)              AS vector_score,
            COALESCE(fs.fts_score, 0)                 AS fts_score
        FROM vector_scores vs
        FULL OUTER JOIN fts_scores fs ON fs.chunk_id = vs.chunk_id
        INNER JOIN documents d ON d.id = COALESCE(vs.document_id, fs.document_id)
    """

    params = {
        "embedding": embedding_str,
        "workspace_id": workspace_id,
        "query": query,
        "prelimit": limit,
    }
    if collection_id:
        params["collection_id"] = collection_id

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    return [
        {
            "chunk_id": row[0],
            "document_id": row[1],
            "document_name": row[2],
            "content": row[3],
            "chunk_index": row[4],
            "vector_score": float(row[5]),
            "fts_score": float(row[6]),
        }
        for row in rows
    ]
