# Knowledge Base — Documentation

A self-hosted, AI-powered document management and semantic search platform. Upload documents, search them semantically, and ask questions — all without sending data to external APIs.

## What it does

- **Document ingestion** — Upload PDF, DOCX, TXT, and Markdown files. Documents are automatically extracted, chunked, and embedded in the background.
- **Hybrid search** — Combines vector similarity (70%) and full-text search (30%) for results that are both semantically relevant and keyword-accurate.
- **RAG chat** — Ask questions in natural language and receive AI-generated answers with source citations, streamed in real time.
- **Multi-tenant workspaces** — Fully isolated workspaces with role-based access control (Owner / Admin / Member / Viewer).
- **Self-hosted AI** — All embeddings and chat responses are generated locally via Ollama. No tokens sent to OpenAI or any cloud provider.

## Stack at a glance

| Layer | Technology |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Database | PostgreSQL 16 + pgvector |
| Task queue | Celery 5 + Redis 7 |
| AI models | Ollama (nomic-embed-text + llama3.2:3b) |
| File storage | MinIO (S3-compatible) |
| Frontend | Vue.js 3 + TypeScript + Pinia |
| Deployment | Docker Compose / Kubernetes |

## Documentation sections

| Section | Description |
|---|---|
| [Getting Started](getting-started.md) | Run the full stack locally in minutes |
| [Hardware Requirements](hardware-requirements.md) | Minimum specs, lite profile, Docker Desktop memory settings |
| [How It Works](how-it-works.md) | Architecture, data flow, and key design decisions |
| [API Reference](api-reference.md) | All REST endpoints with request/response details |
| [Configuration](configuration.md) | Every environment variable explained |
| [Deployment](deployment.md) | Docker Compose and Kubernetes production setup |
| [Security](security.md) | Auth model, RBAC, rate limiting, audit logging |
| [Troubleshooting](troubleshooting.md) | Common problems and fixes |
| [Release Notes](release-notes.md) | Version history and changelog |
