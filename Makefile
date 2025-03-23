.PHONY: dev down build migrate seed test lint format shell logs

# ─── Dev ──────────────────────────────────────────────────────────────────────
dev:
	docker compose up

down:
	docker compose down

build:
	docker compose build

# ─── Database ─────────────────────────────────────────────────────────────────
migrate:
	docker compose run --rm api python manage.py makemigrations
	docker compose run --rm api python manage.py migrate

seed:
	docker compose run --rm api python manage.py seed_demo

# ─── Testing ──────────────────────────────────────────────────────────────────
test:
	docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test api \
		sh -c "pip install --no-cache-dir -q -r requirements-dev.txt && \
		       python -m pytest --cov --cov-report=term-missing -v"

test-fast:
	docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test api \
		sh -c "pip install --no-cache-dir -q -r requirements-dev.txt && \
		       python -m pytest -x -q"

# ─── Code quality ─────────────────────────────────────────────────────────────
lint:
	docker compose run --rm api sh -c "pip install --no-cache-dir -q -r requirements-dev.txt && \
		ruff check . && black --check ."

format:
	docker compose run --rm api sh -c "pip install --no-cache-dir -q -r requirements-dev.txt && \
		ruff check --fix . && black ."

# ─── Utils ────────────────────────────────────────────────────────────────────
shell:
	docker compose run --rm api python manage.py shell_plus

logs:
	docker compose logs -f api worker

superuser:
	docker compose run --rm api python manage.py createsuperuser
