# Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and edit it before starting the stack.

Variables without a default value are **required** in production.

---

## Django core

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | (dev default) | Secret key for signing cookies and tokens. Generate a 50-char random string for production. |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | Use `config.settings.production` in production. |
| `DEBUG` | `True` | Set to `False` in production. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames. |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS allowed origins. |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | Trusted origins for CSRF. |
| `TRUSTED_PROXY_IPS` | _(empty)_ | IPs of trusted reverse proxies (e.g. nginx, load balancer). Used for real IP extraction. |

---

## Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@db:5432/knowledgebase` | Full PostgreSQL DSN. |

The database must have the `pgvector` extension installed. The migration `0001_initial` runs `CREATE EXTENSION IF NOT EXISTS vector` automatically.

---

## Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | Used for rate limiting and session cache. |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery task broker. |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Celery result store. |

---

## File storage (MinIO / S3)

| Variable | Default | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | `minioadmin` | Access key for MinIO or AWS S3. |
| `AWS_SECRET_ACCESS_KEY` | `minioadmin` | Secret key. |
| `AWS_S3_BUCKET_NAME` | `knowledgebase` | Target bucket. The bucket is created automatically on first use. |
| `AWS_S3_ENDPOINT_URL` | `http://minio:9000` | Override for MinIO. Omit (or leave blank) to use real AWS S3. |
| `AWS_S3_REGION_NAME` | `us-east-1` | AWS region (ignored when using MinIO). |
| `PRESIGNED_URL_EXPIRY_SECONDS` | `900` | How long download links are valid (default: 15 minutes). |

---

## Ollama (AI models)

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://ollama:11434/v1` | Ollama OpenAI-compatible API base URL. |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Model used for generating chunk embeddings. Must produce 768-dim vectors unless you change `EMBEDDING_DIMENSIONS`. |
| `OLLAMA_CHAT_MODEL` | `llama3.2:3b` | Model used for chat completions and query rewriting. |
| `EMBEDDING_DIMENSIONS` | `768` | Vector dimensions. Must match the embedding model. Changing this after data has been indexed requires a full re-ingestion. |

---

## Document processing

| Variable | Default | Description |
|---|---|---|
| `CHUNK_SIZE_TOKENS` | `512` | Target chunk size in tokens. |
| `CHUNK_OVERLAP_TOKENS` | `64` | Overlap between consecutive chunks to preserve context. |
| `MAX_UPLOAD_SIZE_MB` | `20` | Maximum file size for a single upload. |
| `MAX_CHUNKS_PER_DOCUMENT` | `5000` | Hard cap on chunks per document to prevent unbounded processing time. |
| `WORKSPACE_STORAGE_QUOTA_MB` | `2048` | Total raw storage allowed per workspace (2 GB default). |
| `EMBEDDING_BATCH_SIZE` | `100` | Number of chunks sent to Ollama per embedding request. |

---

## Search

| Variable | Default | Description |
|---|---|---|
| `SEARCH_VECTOR_WEIGHT` | `0.7` | Weight given to vector similarity in the hybrid score (0.0–1.0). |
| `SEARCH_FTS_WEIGHT` | `0.3` | Weight given to full-text search score. Should sum to 1.0 with `SEARCH_VECTOR_WEIGHT`. |
| `SEARCH_MIN_SCORE` | `0.15` | Chunks with a combined score below this threshold are excluded from results. |
| `SEARCH_FTS_LANGUAGE` | `english` | PostgreSQL text search configuration. Must match the FTS index created in migrations. Changing this requires a manual re-index. |

---

## JWT authentication

| Variable | Default | Description |
|---|---|---|
| `JWT_ALGORITHM` | `HS256` | Signing algorithm. Switch to `RS256` in production (see [Security](security.md)). |
| `JWT_SECRET_KEY` | _(uses `DJANGO_SECRET_KEY`)_ | Override for a dedicated JWT secret. |
| `ACCESS_TOKEN_LIFETIME_MINUTES` | `15` | Access token TTL. |
| `REFRESH_TOKEN_LIFETIME_DAYS` | `7` | Refresh token TTL. |

---

## Rate limiting

| Variable | Default | Description |
|---|---|---|
| `RATELIMIT_ENABLE` | `True` | Set to `False` to disable rate limiting (useful in tests). |
| `LOGIN_RATE_LIMIT` | `5/15m` | Login attempts per IP. |
| `REGISTER_RATE_LIMIT` | `10/h` | Registration attempts per IP. |
| `UPLOAD_RATE_LIMIT` | `30/m` | Document uploads per user. |
| `SEARCH_RATE_LIMIT` | `30/m` | Search queries per user. |
| `CHAT_RATE_LIMIT` | `20/m` | Chat messages per user. |

---

## Production checklist

Before going to production, make sure to:

1. Set `DEBUG=False` and `DJANGO_SETTINGS_MODULE=config.settings.production`
2. Generate a new `DJANGO_SECRET_KEY` (50+ random chars)
3. Set `ALLOWED_HOSTS` and `ALLOWED_ORIGINS` to your actual domain
4. Replace MinIO with AWS S3 (remove `AWS_S3_ENDPOINT_URL`)
5. Switch `JWT_ALGORITHM` to `RS256` and provide a key pair
6. Set `SECURE_HSTS_SECONDS=31536000` (1 year)
7. Review `RATELIMIT_*` values for your expected traffic

See [Deployment](deployment.md) for full production setup instructions.
