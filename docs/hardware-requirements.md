# Hardware Requirements

This document covers what you need to run Knowledge Base locally, and how to tune the setup for the machine you have.

---

## Quick reference

| Profile | RAM | CPU | Disk | GPU | Command |
|---|---|---|---|---|---|
| **Lite** | 8 GB | 4 cores | 12 GB | not required | `docker compose -f docker-compose.lite.yml up -d` |
| **Standard** | 16 GB | 6 cores | 20 GB | not required | `docker compose up -d` |
| **GPU** | 16 GB | 6 cores | 20 GB | NVIDIA (4 GB VRAM) | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` |

---

## Profiles explained

### Lite (`docker-compose.lite.yml`)

Designed for laptops and lower-end desktops. Removes non-essential services and caps memory on all containers.

**What is different from the standard stack:**

| Change | Reason |
|---|---|
| No `worker`, `beat`, `flower` containers | Celery tasks run synchronously inside the API process (`CELERY_TASK_ALWAYS_EAGER=True`) |
| `llama3.2:1b` instead of `llama3.2:3b` | ~1.3 GB less to download; faster inference on CPU |
| `EMBEDDING_BATCH_SIZE=32` (down from 100) | Lower peak memory during document ingestion |
| `mem_limit` on every container | Prevents any single service from consuming all available RAM |
| Redis capped at 48 MB with LRU eviction | Avoids unbounded cache growth |
| No GPU reservation | Works on any machine without NVIDIA drivers |

**Tradeoffs:**

- Document ingestion blocks the HTTP request (no background worker). Uploading a large file will make the API unresponsive for a few seconds.
- `llama3.2:1b` produces shorter, less detailed answers than `3b`. For simple Q&A over short documents the difference is small; for long-form synthesis it is noticeable.
- No Flower dashboard at `http://localhost:5555`.

### Standard (`docker-compose.yml`)

The default profile. Runs all services including a dedicated Celery worker, Celery Beat (scheduled tasks), and Flower (task monitoring). Uses `llama3.2:3b` for better answer quality.

Document ingestion happens in the background — uploading a file returns immediately and the API stays responsive while the worker processes the document.

### GPU (`docker-compose.yml` + `docker-compose.gpu.yml`)

Extends the standard profile with an NVIDIA GPU reservation for the Ollama container. Inference is 5–10× faster compared to CPU-only.

Requirements:
- NVIDIA GPU with at least 4 GB VRAM (8 GB recommended for `3b`)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed on the host
- Docker Engine with GPU support enabled

---

## Disk space breakdown

| Item | Size |
|---|---|
| Docker images (all services) | ~5 GB |
| `nomic-embed-text` model | ~274 MB |
| `llama3.2:1b` model | ~650 MB |
| `llama3.2:3b` model | ~2 GB |
| PostgreSQL data (grows with documents) | variable |
| MinIO file storage (uploaded documents) | variable |

Models are stored in a named Docker volume (`ollama_data`) and are reused across restarts — they are only downloaded once.

---

## Minimum viable setup (8 GB RAM laptop)

1. Use the lite profile.
2. Ensure Docker Desktop is allocated at least 6 GB RAM:
   - Docker Desktop → Settings → Resources → Memory → `6 GB`
3. Close other memory-heavy applications before the first startup (model download is the peak memory moment).
4. First startup takes 5–15 minutes depending on your connection — the Ollama image alone is ~3.2 GB.

```bash
cp .env.example .env
docker compose -f docker-compose.lite.yml up -d
```

---

## Tuning environment variables

These variables in `.env` directly affect resource usage:

| Variable | Default | Lite recommendation | Effect |
|---|---|---|---|
| `OLLAMA_CHAT_MODEL` | `llama3.2:3b` | `llama3.2:1b` | Smaller model, less RAM and faster inference |
| `EMBEDDING_BATCH_SIZE` | `100` | `32` | Chunks embedded per API call; lower = less peak memory |
| `CHUNK_SIZE_TOKENS` | `512` | `256` | Smaller chunks = more but smaller embeddings |
| `MAX_CHUNKS_PER_DOCUMENT` | `5000` | `1000` | Cap on chunks per document |
| `WORKSPACE_STORAGE_QUOTA_MB` | `2048` | `512` | Per-workspace upload limit |

---

## Docker Desktop memory allocation

By default Docker Desktop on Windows and macOS limits the VM to 2 GB RAM, which is not enough to run this stack. You must increase it:

1. Open Docker Desktop.
2. Go to **Settings → Resources → Advanced**.
3. Set **Memory** to at least `6 GB` (lite) or `12 GB` (standard).
4. Click **Apply & Restart**.

---

## What to do if a container runs out of memory

Check which container was OOM-killed:

```bash
docker compose ps
docker stats --no-stream
```

If `ollama` is the problem, increase its `mem_limit` in the compose file or reduce the model size. If `api` is the problem, lower `EMBEDDING_BATCH_SIZE` further.
