from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost").split(",")

# JWT signing key — kept separate from Django's SECRET_KEY so that
# leaking one (e.g. via a debug page) does not compromise the other.
JWT_ALGORITHM = config("JWT_ALGORITHM", default="HS256")
JWT_SIGNING_KEY = config("JWT_SIGNING_KEY", default=SECRET_KEY)
JWT_VERIFYING_KEY = config("JWT_VERIFYING_KEY", default="")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "django_extensions",
]

LOCAL_APPS = [
    "apps.authentication",
    "apps.workspaces",
    "apps.collections",
    "apps.documents",
    "apps.search",
    "apps.chat",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files (admin, Swagger UI) directly from the app,
    # so DEBUG=False deployments behind a plain proxy still get their assets.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.RequestIDMiddleware",
    "common.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = "authentication.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "common.pagination.CursorPagination",
    "PAGE_SIZE": 20,
}

# ─── JWT ──────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("ACCESS_TOKEN_LIFETIME_MINUTES", default=15, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": JWT_ALGORITHM,
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "VERIFYING_KEY": JWT_VERIFYING_KEY or None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config("ALLOWED_ORIGINS", default="http://localhost:5173").split(",")
# Auth is stateless Bearer tokens (no cookies), so credentialed CORS is not
# needed. Keeping it off avoids unnecessarily broadening the cross-origin surface.
CORS_ALLOW_CREDENTIALS = False

# ─── Celery ───────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True

# ─── S3 / MinIO ───────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config("AWS_S3_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_PRESIGNED_URL_EXPIRY = 900  # 15 minutes

# ─── Ollama ───────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = config("OLLAMA_BASE_URL", default="http://ollama:11434/v1")
OLLAMA_EMBEDDING_MODEL = config("OLLAMA_EMBEDDING_MODEL", default="nomic-embed-text")
OLLAMA_CHAT_MODEL = config("OLLAMA_CHAT_MODEL", default="llama3.2:3b")
OLLAMA_MAX_RETRIES = config("OLLAMA_MAX_RETRIES", default=3, cast=int)
EMBEDDING_DIMENSIONS = 768

# ─── Document processing ──────────────────────────────────────────────────────
CHUNK_SIZE_TOKENS = config("CHUNK_SIZE_TOKENS", default=512, cast=int)
CHUNK_OVERLAP_TOKENS = config("CHUNK_OVERLAP_TOKENS", default=64, cast=int)
EMBEDDING_BATCH_SIZE = config("EMBEDDING_BATCH_SIZE", default=100, cast=int)
# TTL (seconds) for per-chunk embedding checkpoints so a retried ingest resumes
# instead of re-embedding the whole document. Must outlast the retry backoff.
EMBEDDING_CHECKPOINT_TTL = config("EMBEDDING_CHECKPOINT_TTL", default=3600, cast=int)
MAX_UPLOAD_SIZE_MB = config("MAX_UPLOAD_SIZE_MB", default=20, cast=int)
MAX_CHUNKS_PER_DOCUMENT = config("MAX_CHUNKS_PER_DOCUMENT", default=5000, cast=int)
WORKSPACE_STORAGE_QUOTA_MB = config("WORKSPACE_STORAGE_QUOTA_MB", default=2048, cast=int)
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}

# ─── Search ───────────────────────────────────────────────────────────────────
SEARCH_VECTOR_WEIGHT = config("SEARCH_VECTOR_WEIGHT", default=0.7, cast=float)
SEARCH_FTS_WEIGHT = config("SEARCH_FTS_WEIGHT", default=0.3, cast=float)
SEARCH_MIN_SCORE = config("SEARCH_MIN_SCORE", default=0.15, cast=float)
# PostgreSQL FTS text-search configuration. Must match the language used by the
# functional GIN index in documents migration 0003; changing it requires a new
# index migration to keep the index usable.
SEARCH_FTS_LANGUAGE = config("SEARCH_FTS_LANGUAGE", default="english")
QUERY_EMBEDDING_CACHE_TTL = config("QUERY_EMBEDDING_CACHE_TTL", default=300, cast=int)

# ─── Rate limiting ────────────────────────────────────────────────────────────
RATELIMIT_ENABLE = config("RATELIMIT_ENABLE", default=True, cast=bool)
RATELIMIT_USE_CACHE = "default"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://redis:6379/0"),
    }
}

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "common.logging.JSONFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}

# ─── API Docs ─────────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Knowledge Base API",
    "DESCRIPTION": "Internal knowledge base with natural language search",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ─── Security headers ─────────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Content Security Policy — empty in dev, hardened in production.py.
CONTENT_SECURITY_POLICY = config("CONTENT_SECURITY_POLICY", default="")

# Reverse proxies whose X-Forwarded-For we trust when extracting the real client IP.
TRUSTED_PROXY_IPS: list[str] = []
