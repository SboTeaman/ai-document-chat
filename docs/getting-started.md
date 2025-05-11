# Getting Started

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- 8 GB RAM minimum — see [Hardware Requirements](hardware-requirements.md) for profile-specific specs
- ~12 GB free disk space (Docker images + model weights)

> **Low-end machine?** Use the lite profile: `docker compose -f docker-compose.lite.yml up -d`
> It removes non-essential services and uses a smaller AI model. See [Hardware Requirements](hardware-requirements.md).

## 1. Clone and configure

```bash
git clone <repo-url>
cd AI-document-chat
cp .env.example .env
```

The defaults in `.env.example` work out of the box for local development. You do not need to change anything to get started.

## 2. Start the stack

```bash
docker compose up
```

This starts eight services: PostgreSQL, Redis, MinIO, the Django API, a Celery worker, Celery Beat, Flower (task monitor), the Vue.js frontend, and Ollama.

First startup pulls Docker images and downloads the Ollama models — expect 5–10 minutes on a fast connection.

## 3. Run database migrations

In a second terminal:

```bash
make migrate
```

## 4. Load demo data (optional)

```bash
make seed
```

This creates a demo workspace and a test user (`demo@example.com` / `demo1234`).

## 5. Open the app

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API (Swagger UI) | http://localhost:8000/api/docs/ |
| Django Admin | http://localhost:8000/admin/ |
| Flower (Celery) | http://localhost:5555 |
| MinIO Console | http://localhost:9001 |

## 6. Create your first workspace

1. Register a new account at http://localhost:5173
2. Create a workspace
3. Upload a document — status will move from **Queued → Processing → Ready** within ~30 seconds
4. Use the **Search** tab to run semantic queries
5. Use the **Chat** tab to ask questions with source citations

## Development commands

```bash
make dev           # start all containers (alias for docker compose up)
make down          # stop and remove containers
make build         # rebuild Docker images after code changes
make migrate       # run makemigrations + migrate
make test          # run the full Pytest suite with coverage
make test-fast     # stop on first failure (-x -q)
make lint          # Ruff + Black check (no changes)
make format        # Ruff --fix + Black (apply changes)
make shell         # open Django shell_plus
make logs          # tail api + worker logs
make superuser     # create a Django superuser interactively
```

### Frontend (outside Docker)

```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173 with HMR
npm run lint       # ESLint
npm run typecheck  # vue-tsc
npm run test       # Vitest (watch mode)
npm run build      # production build + type-check
```

## Switching AI models

Edit `.env` and restart the `api` and `worker` services:

```env
OLLAMA_EMBEDDING_MODEL=nomic-embed-text   # 768-dim embeddings
OLLAMA_CHAT_MODEL=llama3.2:3b             # chat / RAG responses
```

Any model available in the [Ollama library](https://ollama.com/library) can be used. After changing the embedding model you must re-process all documents (delete and re-upload), because embedding dimensions are stored in the database and must be consistent.
