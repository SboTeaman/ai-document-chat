import os

from .base import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("TEST_DB_NAME", "knowledgebase_test"),
        "USER": os.environ.get("TEST_DB_USER", "kb_user"),
        "PASSWORD": os.environ.get("TEST_DB_PASSWORD", "kb_password"),
        "HOST": os.environ.get("TEST_DB_HOST", "db"),
        "PORT": os.environ.get("TEST_DB_PORT", "5432"),
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

RATELIMIT_ENABLE = False

OPENAI_API_KEY = "test-key"
AWS_ACCESS_KEY_ID = "test"
AWS_SECRET_ACCESS_KEY = "test"
AWS_STORAGE_BUCKET_NAME = "test-bucket"
AWS_S3_ENDPOINT_URL = os.environ.get("TEST_S3_ENDPOINT_URL", "http://minio:9000")
