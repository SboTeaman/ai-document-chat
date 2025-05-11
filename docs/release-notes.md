# Release Notes

## v1.0.0 — Initial release

### Features

**Document management**
- Upload PDF, DOCX, TXT, and Markdown files (up to 20 MB)
- Asynchronous ingestion pipeline: extraction → chunking (512-token chunks, 64-token overlap) → embedding
- Real-time status tracking (QUEUED → PROCESSING → READY / FAILED)
- Presigned download URLs with 15-minute expiry
- Per-workspace storage quota (default 2 GB)

**Search**
- Hybrid search combining vector similarity (pgvector HNSW) and PostgreSQL full-text search
- Weighted scoring: 70% vector + 30% FTS (configurable)
- Collection-scoped search
- Minimum score threshold filtering

**RAG chat**
- Multi-turn chat sessions with conversation history
- Query rewriting for follow-up questions
- Server-Sent Events (SSE) streaming of responses
- Source citations with document name and chunk index
- Prompt injection protection via system prompt sandboxing

**Multi-tenancy**
- Fully isolated workspaces with slug-based naming
- Four-role RBAC: Owner / Admin / Member / Viewer
- Member invitation and role management
- Append-only audit log for sensitive operations

**Infrastructure**
- Self-hosted AI via Ollama (no external API costs or data egress)
- Default models: `nomic-embed-text` (embeddings) + `llama3.2:3b` (chat)
- Docker Compose stack for local development and simple production deployments
- Kubernetes manifests (Kustomize) with HPA, Ingress, and a pre-deployment migration job
- GitHub Actions CI: lint, test, build, K8s manifest validation

**Security**
- JWT authentication with token rotation and blacklisting
- Redis-backed rate limiting on all sensitive endpoints
- MIME type validation via magic bytes
- Security response headers (X-Frame-Options, X-Content-Type-Options, etc.)
- Tenant isolation enforced at the ORM layer

---

## Upcoming

The following features are planned for future releases:

- **Reranking** — cross-encoder reranking of search results for improved relevance
- **Document versioning** — upload a new version of a document without losing history
- **Webhook notifications** — notify external systems when document processing completes
- **SSO / OIDC** — single sign-on via an external identity provider
- **Streaming progress** — real-time ingestion progress updates (not just status polling)
- **Bulk upload** — upload a ZIP archive or multiple files in a single request
- **Export chat** — download a chat session as Markdown or PDF

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — breaking API changes or incompatible data model changes requiring a migration
- **MINOR** — new features that are backwards-compatible
- **PATCH** — bug fixes and security patches

Changes that require re-indexing documents (e.g. changing embedding model defaults or chunking parameters) are considered **MAJOR** and will be clearly called out in release notes.
