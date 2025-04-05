import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """Report liveness of DB + Redis (and, with ``?deep=1``, Ollama + storage).

        Returns 200 when all checked components are healthy, else 503.
        """
        checks = {"database": False, "redis": False, "ollama": False, "storage": False}

        try:
            connection.ensure_connection()
            checks["database"] = True
        except Exception as exc:
            logger.error("Health check DB failed", extra={"error": str(exc)})

        try:
            cache.set("health_check", "ok", timeout=5)
            checks["redis"] = cache.get("health_check") == "ok"
        except Exception as exc:
            logger.error("Health check Redis failed", extra={"error": str(exc)})

        deep = request.query_params.get("deep") == "1"
        if deep:
            try:
                import urllib.request

                base = settings.OLLAMA_BASE_URL.rstrip("/").removesuffix("/v1")
                # URL is built from a trusted internal setting, not user input.
                with urllib.request.urlopen(f"{base}/api/tags", timeout=2) as resp:  # noqa: S310
                    checks["ollama"] = 200 <= resp.status < 300
            except Exception as exc:
                logger.error("Health check Ollama failed", extra={"error": str(exc)})

            try:
                from common.storage import get_s3_client

                client = get_s3_client()
                client.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
                checks["storage"] = True
            except Exception as exc:
                logger.error("Health check Storage failed", extra={"error": str(exc)})
        else:
            checks.pop("ollama")
            checks.pop("storage")

        all_healthy = all(checks.values())
        status_code = 200 if all_healthy else 503
        return Response({"status": "ok" if all_healthy else "degraded", "checks": checks}, status=status_code)
