# How It Works

## High-level architecture

```
Browser (Vue 3)
     │  REST + SSE
     ▼
Django REST API  ──────►  PostgreSQL + pgvector
     │                       ▲
     │  Celery tasks          │ embeddings
     ▼                       │
Celery Worker  ──► Ollama (nomic-embed-text)
     │
     └──► MinIO (raw files)

Chat requests:
Django ──► Ollama (llama3.2:3b)  ──SSE──► Browser
```

All AI inference stays inside the cluster. No data is sent to external services.

---

## Document ingestion pipeline

When a user uploads a file, a four-stage async pipeline runs via Celery:

### Stage 1 — Validation & storage
The API validates the file (MIME type via magic bytes, max 20 MB, workspace quota), stores the raw bytes in MinIO under a random UUID key, and creates a `Document` record with status `QUEUED`.

### Stage 2 — Text extraction (`tasks/extraction.py`)
A Celery task picks up the document and extracts plain text:
- **PDF** — `pdfplumber` (page-by-page)
- **DOCX** — `python-docx` (paragraph-by-paragraph)
- **TXT / MD** — direct read with encoding detection

### Stage 3 — Chunking (`tasks/chunking.py`)
The extracted text is split into overlapping chunks using `tiktoken`:
- Chunk size: **512 tokens**
- Overlap: **64 tokens** (prevents context loss at chunk boundaries)
- Maximum chunks per document: **5000** (configurable via `MAX_CHUNKS_PER_DOCUMENT`)

Each chunk is stored as a `DocumentChunk` row.

### Stage 4 — Embedding (`tasks/embedding.py`)
Chunks are sent to Ollama's `nomic-embed-text` model in batches of 100. Each batch produces 768-dimensional float vectors, stored in the `embedding` column (pgvector `VectorField`).

On completion the document status is set to `READY`. On any failure the status becomes `FAILED` and the error message is recorded.

---

## Hybrid search

A single search query triggers two parallel database queries, then the results are merged:

### Vector search
The query string is embedded using the same Ollama model. The resulting vector is compared against all chunk embeddings using **cosine similarity** via pgvector's HNSW index:

```sql
SELECT chunk_id, 1 - (embedding <=> query_vector) AS score
FROM document_chunks
WHERE workspace_id = ?
ORDER BY embedding <=> query_vector
LIMIT n;
```

The HNSW (Hierarchical Navigable Small World) index provides approximate nearest-neighbour search without requiring a training step, and scales well to millions of chunks.

### Full-text search
The query is also run against PostgreSQL's built-in FTS engine using `to_tsvector('english', content)`. This catches exact keyword matches that may have low vector similarity (product codes, names, abbreviations).

### Score fusion
Results from both passes are merged with weighted scoring:

```
final_score = 0.7 × vector_score + 0.3 × fts_score
```

Results below `SEARCH_MIN_SCORE=0.15` are discarded. The top `limit` (default 10) chunks are returned.

---

## RAG chat pipeline

```
User message
     │
     ▼
[Query rewriting]  ← chat history (last N turns)
  Ollama rewrites follow-up questions into standalone queries
     │
     ▼
[Context retrieval]
  Hybrid search → top 5 most relevant chunks
     │
     ▼
[Prompt assembly]
  System prompt + retrieved context + conversation history + user message
     │
     ▼
[LLM generation]
  Ollama streams tokens via SSE to the browser
     │
     ▼
[Citation tracking]
  After streaming completes, citations are extracted from the response
  and stored in ChatMessage.citations (JSON array)
```

The system prompt explicitly treats document content as **untrusted data**, preventing prompt injection attacks where a malicious document could instruct the LLM to ignore previous instructions.

---

## Multi-tenancy and RBAC

Every resource (collection, document, search query, chat session) belongs to a workspace. All database queries include a `workspace_id` filter — there is no shared data between workspaces.

Each workspace member has one of four roles:

| Role | Read | Upload | Manage collections | Manage members | Delete workspace |
|---|:---:|:---:|:---:|:---:|:---:|
| Viewer | ✓ | | | | |
| Member | ✓ | ✓ | | | |
| Admin | ✓ | ✓ | ✓ | ✓ | |
| Owner | ✓ | ✓ | ✓ | ✓ | ✓ |

Role checks are enforced at the view layer via `common/permissions.py`.

---

## Key design decisions

### pgvector instead of a dedicated vector database
PostgreSQL handles both vector similarity search and relational filtering (workspace isolation, collection scope) in a single query. No extra service to operate or keep in sync.

### HNSW index
Unlike IVFFlat, HNSW does not require a training step or a minimum row count. It provides consistent recall from the first document and scales up gracefully.

### SSE instead of WebSockets for chat streaming
Chat responses are strictly server-to-client (unidirectional). SSE is simpler than WebSockets and works natively with Django without a separate ASGI server — the streaming view uses Django's `StreamingHttpResponse`.

### Celery for document processing
Embedding generation takes 5–30 seconds per document. Async processing via Celery prevents HTTP request timeouts and lets users see real-time status updates by polling the document endpoint.

### Presigned URLs for file downloads
Raw files are stored in MinIO under random UUID keys that are never exposed to clients. The download endpoint generates a short-lived presigned URL (15 minutes) and redirects the client. This ensures that access to files is always auth-checked and audit-logged, even when the client directly hits MinIO.
