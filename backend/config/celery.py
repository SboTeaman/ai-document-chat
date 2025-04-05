"""Celery application bootstrap: builds the app, loads CELERY_* settings from
Django, and auto-discovers `tasks` modules across installed apps."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("knowledgebase")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
