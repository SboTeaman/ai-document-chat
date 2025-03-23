# Knowledge Base

Internal knowledge base with natural language search and AI-powered Q&A. Upload documents (PDF, DOCX, TXT, MD), search them semantically, or ask questions and get cited answers streamed in real time — all without sending data to external APIs.

**Knowledge Base** is a self-hosted document management system with a built-in AI search engine and chatbot.

Here's how it works in practice:

1. **Upload documents** (PDF, DOCX, TXT, Markdown) into a workspace. The system processes them automatically in the background — it extracts the text, splits it into chunks, and converts each chunk into a numerical vector (embedding) using a local AI model running via Ollama.

2. **Search in plain language.** Instead of matching exact keywords, the search engine understands the meaning of your query — "what are the payment terms?" will surface the right passages even if the document uses different phrasing. Under the hood it combines semantic vector search with classic full-text search.

3. **Ask the chatbot** anything about your uploaded documents. You get a real-time streamed answer with citations showing exactly which documents each piece of information came from.

Everything runs **without sending data outside your infrastructure** — AI models run locally via Ollama, files are stored in MinIO (a local S3-compatible store), and the database is PostgreSQL. It's designed for company documents, contracts, internal wikis — anywhere data cannot go to OpenAI or other external services.

Supports multiple users with workspace isolation and four permission roles: Owner, Admin, Member, and Viewer.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · Django 5 · Django REST Framework |
| AI / Search | Ollama `nomic-embed-text` (embeddings, 768-dim) · Ollama `llama3.2:3b` (chat) · pgvector (HNSW) · PostgreSQL FTS |
| Async pipeline | Celery · Redis |
| Storage | MinIO (S3-compatible) |
| Frontend | Vue.js 3 · TypeScript · Vite · Vitest · ESLint |
| Infrastructure | Docker · Docker Compose · Kubernetes (Kustomize) · GitHub Actions CI |

## Quick start

```bash
cp .env.example .env
docker compose up        # pulls Ollama models on first run (~5 min)
make migrate
make seed                # demo workspace + user
```

Open:
- **Frontend** → http://localhost:5173 — `demo@example.com` / `Demo1234!`
- **API docs** → http://localhost:8000/api/docs/
- **Admin** → http://localhost:8000/admin/
- **Flower** (Celery monitor) → http://localhost:5555

→ Full setup guide and dev commands: [docs/getting-started.md](docs/getting-started.md)

## Architecture

```
Browser (Vue.js)
    │
    ├── REST API (Django + DRF) ──→ PostgreSQL + pgvector
    │                           ──→ Redis (cache + rate limiting)
    │                           ──→ MinIO (file storage)
    │
    └── SSE stream (chat) ──→ Ollama API (streaming)

Celery Worker (async)
    ├── Download file from MinIO
    ├── Extract text (pdfplumber / python-docx)
    ├── Chunk text (tiktoken, 512 tok, 64 overlap)
    ├── Generate embeddings (Ollama nomic-embed-text, 768-dim, batches of 100)
    └── Save to pgvector (HNSW index, cosine distance)
```

→ Detailed breakdown of each pipeline stage: [docs/how-it-works.md](docs/how-it-works.md)

## Project structure

```
backend/
├── apps/
│   ├── authentication/   # JWT auth, custom User, AuditLog
│   ├── workspaces/       # multi-tenant, RBAC
│   ├── collections/      # document grouping
│   ├── documents/        # upload + async ingestion pipeline
│   │   └── tasks/        # extraction → chunking → embedding
│   ├── search/           # hybrid vector + FTS service
│   └── chat/             # RAG pipeline, SSE streaming
├── common/               # permissions, middleware, exceptions, storage
├── config/               # Django settings, celery, urls
└── tests/                # pytest, factory_boy, mocked Ollama

frontend/
├── Dockerfile            # multi-stage build → nginx (serves the SPA)
└── src/
    ├── views/            # Login, Workspace, Search, Chat, Members
    ├── stores/           # Pinia (auth) — unit-tested with Vitest
    ├── lib/              # markdown/sanitisation, toast, theme
    └── api/              # axios client, endpoint wrappers

k8s/                      # Kustomize bundle: deployments, ingress, HPA, jobs
docs/                     # project documentation
```

## Documentation

| | |
|---|---|
| [Getting Started](docs/getting-started.md) | Local setup, dev commands, switching models |
| [How It Works](docs/how-it-works.md) | Ingestion pipeline, hybrid search, RAG, design decisions |
| [API Reference](docs/api-reference.md) | All endpoints, request/response shapes, SSE events |
| [Configuration](docs/configuration.md) | Every environment variable explained |
| [Deployment](docs/deployment.md) | Docker Compose, Kubernetes, CI/CD, backups |
| [Security](docs/security.md) | Auth model, RBAC, rate limiting, audit logging |
| [Troubleshooting](docs/troubleshooting.md) | Common problems and fixes |
| [Release Notes](docs/release-notes.md) | Changelog and upcoming features |
