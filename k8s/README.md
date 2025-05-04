# Kubernetes deployment

Kustomize bundle for the Knowledge Base. Assumes managed PostgreSQL (pgvector),
Redis, and S3 (or a self-hosted equivalent) reachable from the cluster.

## Contents

| File | Purpose |
|---|---|
| `namespace.yaml` | `knowledge-base` namespace |
| `configmap.yaml` | non-secret runtime config |
| `secret.example.yaml` | **template** — copy to `secret.yaml`, fill in, keep out of git |
| `migrate-job.yaml` | runs `migrate` + `collectstatic` |
| `api.yaml` | Django/Gunicorn Deployment + Service (probes on `/health/`) |
| `workers.yaml` | Celery worker + singleton beat |
| `frontend.yaml` | nginx-served SPA Deployment + Service |
| `ingress.yaml` | TLS Ingress; path routing + SSE-friendly (buffering off) |
| `hpa.yaml` | CPU autoscaling for api and worker |
| `kustomization.yaml` | ties it together; pin image tags here |

## Apply

```bash
cp secret.example.yaml secret.yaml      # edit real values (or use external-secrets)
kustomize edit set image \
  knowledge-base-backend=<registry>/kb-backend:<tag> \
  knowledge-base-frontend=<registry>/kb-frontend:<tag>
kubectl apply -k .
```

## Validate locally

```bash
kustomize build . | kubeconform -strict -ignore-missing-schemas -summary -
```

## Notes

- `kb-beat` is a singleton (`replicas: 1`, `Recreate`) — two schedulers would
  double-fire periodic tasks.
- Probes send `X-Forwarded-Proto: https` so `SECURE_SSL_REDIRECT` doesn't bounce them.
- For real AWS S3, drop `AWS_S3_ENDPOINT_URL` and prefer IRSA/pod-identity over
  static keys in the Secret.
