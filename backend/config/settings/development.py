from .base import *  # noqa: F401, F403
from decouple import config

DEBUG = True
# Set CELERY_TASK_ALWAYS_EAGER=True in .env (or docker-compose.lite.yml) to run
# document ingestion tasks synchronously without a separate worker container.
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
