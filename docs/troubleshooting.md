# Troubleshooting

## Documents stuck in PROCESSING or QUEUED

**Symptom:** Document status never advances from `QUEUED` or stays in `PROCESSING` indefinitely.

**Likely cause:** The Celery worker is not running, or Ollama is unreachable.

**Fix:**
```bash
# Check if the worker is running
docker compose ps worker

# View worker logs
docker compose logs worker --tail=50

# Restart the worker
docker compose restart worker
```

If the worker is running but tasks are not being picked up, check the broker:
```bash
docker compose logs redis --tail=20
# Redis should show "Ready to accept connections"
```

If the task is failing during embedding, Ollama may be unreachable or the model not yet downloaded:
```bash
docker compose logs ollama --tail=50
# Look for "model 'nomic-embed-text' not found" or connection errors
```

Pull the models manually if needed:
```bash
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull llama3.2:3b
```

---

## Chat responses are very slow or time out

**Likely cause:** The Ollama chat model is running on CPU. Inference on CPU is much slower than on GPU.

**Check:** Look for `llm load: model loaded successfully` in Ollama logs. If it says `using CPU`, the model is running without GPU acceleration.

**Fix (GPU):** See [Deployment → GPU support](deployment.md) for Kubernetes GPU configuration.

**Workaround (CPU):** Switch to a smaller model in `.env`:
```env
OLLAMA_CHAT_MODEL=llama3.2:1b
```
Then restart the `api` and `worker` containers.

Also check if the nginx proxy has `proxy_buffering off` — without it, the SSE stream is buffered and the user sees nothing until the full response is complete.

---

## "pgvector extension not found" error on startup

**Symptom:** The API container fails to start with `extension "vector" is not available`.

**Fix:** The pgvector extension is pre-installed in the `pgvector/pgvector:pg16` image used in `docker-compose.yml`. If you're using a custom PostgreSQL image, install it manually:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Or use the official image:
```yaml
# docker-compose.yml
services:
  db:
    image: pgvector/pgvector:pg16
```

---

## "Workspace storage quota exceeded" on upload

**Symptom:** Upload returns `400` with `"Workspace storage quota exceeded"`.

**Fix:** Increase the quota for the workspace in the Django admin at `/admin/workspaces/workspace/`, or raise the default in `.env`:
```env
WORKSPACE_STORAGE_QUOTA_MB=4096   # 4 GB
```

To see current usage per workspace:
```bash
docker compose exec api python manage.py shell_plus
# In the shell:
from apps.documents.models import Document
from django.db.models import Sum
Document.objects.values('workspace__name').annotate(total=Sum('file_size_bytes'))
```

---

## Search returns no results or low-quality results

**Symptom:** Search returns nothing even for queries that should match, or returns irrelevant chunks.

**Possible causes and fixes:**

1. **Documents are not yet indexed.** Check document status — only `READY` documents are searchable.

2. **Score threshold is too high.** Lower `SEARCH_MIN_SCORE` in `.env`:
   ```env
   SEARCH_MIN_SCORE=0.05
   ```

3. **FTS language mismatch.** If your documents are not in English, change the FTS language:
   ```env
   SEARCH_FTS_LANGUAGE=german
   ```
   This requires recreating the FTS index (a new migration).

4. **Wrong embedding model.** If you changed `OLLAMA_EMBEDDING_MODEL` after uploading documents, the stored embeddings are incompatible with the new model. Delete all documents and re-upload them.

---

## Rate limit errors (429) in development

**Symptom:** Getting `429 Too Many Requests` during development or testing.

**Fix:** Disable rate limiting for local development:
```env
RATELIMIT_ENABLE=False
```

Or increase the limits:
```env
UPLOAD_RATE_LIMIT=1000/m
SEARCH_RATE_LIMIT=1000/m
CHAT_RATE_LIMIT=1000/m
```

---

## Frontend shows blank page or "Network Error"

**Symptom:** The Vue app loads but all API calls fail.

**Check:** Open the browser developer tools → Network tab. If requests go to the wrong URL, check the Vite proxy config in `frontend/vite.config.ts`.

**Fix:** Make sure `VITE_API_URL` in `.env` points to the API:
```env
VITE_API_URL=http://localhost:8000
```

If running in Docker, the frontend container communicates with the API via the internal Docker network name (`api`), not `localhost`.

---

## JWT token refresh loop

**Symptom:** The browser makes repeated calls to `/api/auth/token/refresh/` without stopping, or users are logged out immediately after logging in.

**Likely cause:** The refresh token has expired, is blacklisted, or the clock skew between client and server exceeds the token lifetime.

**Fix:**
- Check server time: `docker compose exec api date`
- Ensure the server time matches the host: `date` on the host machine
- Clear browser `localStorage` and log in again

---

## Celery Beat not running scheduled tasks

**Symptom:** Periodic tasks (e.g. cleanup of expired sessions) are not running.

**Fix:** Ensure the `beat` service is running. It must be a **single replica** — multiple beat instances cause duplicate task execution:

```bash
docker compose ps beat
docker compose logs beat --tail=30
```

If using Kubernetes, verify the `beat` deployment has `replicas: 1` and no HPA attached.

---

## Database migrations fail

**Symptom:** `make migrate` exits with an error about conflicting migrations.

**Fix:** Check for unapplied migrations:
```bash
docker compose exec api python manage.py showmigrations
```

If a migration is in a broken state, inspect it:
```bash
docker compose exec api python manage.py migrate --plan
```

Never manually delete migration files. If you need to squash migrations, use `python manage.py squashmigrations` and keep the original files until all deployments are on the new squash.

---

## Getting help

1. Check container logs: `docker compose logs <service> --tail=100`
2. Open the Django shell: `make shell`
3. Inspect the Celery task queue in Flower: http://localhost:5555
4. Check the Django admin for error messages on failed documents: http://localhost:8000/admin/documents/document/
