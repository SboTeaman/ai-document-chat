from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False

# Hosts / CSRF must be set explicitly in production env.
ALLOWED_HOSTS = config("ALLOWED_HOSTS").split(",")
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="").split(",")

# Force HTTPS — assume Django sits behind a TLS-terminating proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# Content Security Policy — enforced by SecurityHeadersMiddleware.
CONTENT_SECURITY_POLICY = config(
    "CONTENT_SECURITY_POLICY",
    default=(
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
)

# Trusted proxy IPs used for parsing X-Forwarded-For in audit logs.
TRUSTED_PROXY_IPS = [ip.strip() for ip in config("TRUSTED_PROXY_IPS", default="").split(",") if ip.strip()]

# Logging — keep DEBUG off for the apps logger in prod.
LOGGING["loggers"]["apps"]["level"] = "INFO"  # noqa: F405
