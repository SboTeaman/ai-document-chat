# Deployment

## Docker Compose (recommended for small teams)

Docker Compose is the simplest production option for a single-node setup.

### 1. Prepare the server

```bash
# Install Docker and Docker Compose v2
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with production values. Key changes from defaults:

```env
DEBUG=False
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<50-char random string>
ALLOWED_HOSTS=kb.yourdomain.com
ALLOWED_ORIGINS=https://kb.yourdomain.com

# Use AWS S3 instead of local MinIO
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_S3_BUCKET_NAME=your-bucket
# AWS_S3_ENDPOINT_URL=   <-- leave unset for real S3

# Strong DB password
DATABASE_URL=postgresql://user:strongpassword@db:5432/knowledgebase
```

### 3. Start the stack

```bash
docker compose -f docker-compose.yml up -d
make migrate
```

### 4. Create an admin user

```bash
make superuser
```

### 5. Reverse proxy (nginx example)

```nginx
server {
    listen 443 ssl;
    server_name kb.yourdomain.com;

    ssl_certificate     /etc/ssl/kb.crt;
    ssl_certificate_key /etc/ssl/kb.key;

    # Frontend SPA
    location / {
        proxy_pass http://localhost:5173;
    }

    # Backend API
    location ~ ^/(api|admin|static|health) {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # Required for SSE streaming
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

The `proxy_buffering off` directive is required for chat SSE streaming to reach clients in real time.

---

## Kubernetes

Kubernetes manifests are in `k8s/` and use Kustomize.

### Services deployed

| Service | Replicas | Notes |
|---|---|---|
| `api` | 2 (HPA: 2–10) | Django + gunicorn |
| `worker` | 2 (HPA: 2–6) | Celery worker |
| `beat` | 1 | Celery Beat (scheduler) — must be single replica |
| `frontend` | 2 | nginx SPA |
| `postgres` | 1 | StatefulSet with PVC |
| `redis` | 1 | StatefulSet with PVC |
| `minio` | 1 | StatefulSet with PVC |
| `ollama` | 1 | StatefulSet with PVC (model weights) |

### Deploy

```bash
# 1. Create secrets from the example
cp k8s/secret.example.yaml k8s/secret.yaml
# Edit k8s/secret.yaml with base64-encoded values

# 2. Apply all manifests
kubectl apply -k k8s/

# 3. Run DB migration job (runs automatically pre-deployment)
kubectl wait --for=condition=complete job/migrate --timeout=120s

# 4. Check rollout
kubectl rollout status deployment/api
kubectl rollout status deployment/worker
```

### Ingress

The ingress routes traffic by path prefix:

| Path prefix | Backend |
|---|---|
| `/api/*` | `api` service |
| `/admin/*` | `api` service |
| `/static/*` | `api` service |
| `/health` | `api` service |
| `/*` | `frontend` service (SPA fallback) |

TLS is configured in `ingress.yaml`. Update the `host` and `secretName` fields before deploying.

### Secrets

Never commit `k8s/secret.yaml`. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, Sealed Secrets) to inject secrets at deploy time.

### Autoscaling

HPA is configured for `api` and `worker`:
- `api`: scale on CPU (target 70%), min 2 / max 10 replicas
- `worker`: scale on CPU (target 60%), min 2 / max 6 replicas

### GPU support for Ollama

If your nodes have GPUs, add a node selector and resource request to `k8s/ollama.yaml`:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
nodeSelector:
  accelerator: nvidia-tesla-t4
```

---

## CI/CD (GitHub Actions)

The workflow at `.github/workflows/ci.yml` runs on every push and PR:

| Job | What it does |
|---|---|
| `lint-backend` | Ruff + Black check |
| `test-backend` | Pytest with coverage → Codecov |
| `lint-frontend` | ESLint + vue-tsc + Vitest |
| `build-backend` | Docker build (cached) |
| `build-frontend` | Docker build (cached) |
| `validate-k8s` | kubeconform on all manifests |

To deploy automatically on merge to `main`, add a deploy job that runs `kubectl apply -k k8s/` after the build jobs succeed and your images are pushed to a registry.

---

## Backup and restore

### Database

```bash
# Backup
docker compose exec db pg_dump -U postgres knowledgebase | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
gunzip -c backup_20240101.sql.gz | docker compose exec -T db psql -U postgres knowledgebase
```

The `DocumentChunk.embedding` column is large. For space efficiency, consider excluding embeddings from backups and re-processing documents after restore. Embeddings can be regenerated from the raw files stored in MinIO/S3.

### MinIO (raw files)

Use `mc mirror` (MinIO Client) to sync to a backup bucket:

```bash
mc mirror minio/knowledgebase s3/knowledgebase-backup
```

Or use any S3-compatible backup tool (rclone, aws s3 sync, etc.).
