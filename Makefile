# One-command workflows. `make dev` is all a fresh clone needs.
PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin
PY     := $(BIN)/python

.DEFAULT_GOAL := help
.PHONY: help install dev run migrate seed test cov lint fmt check up down screenshots clean

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

$(BIN)/activate: requirements.txt requirements-dev.txt
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --quiet --upgrade pip
	$(BIN)/pip install --quiet -r requirements-dev.txt
	@touch $(BIN)/activate

install: $(BIN)/activate ## Create .venv and install pinned dependencies

.env:
	cp .env.example .env

dev: install .env migrate seed run ## Set everything up and start the dev server (SQLite, demo data)

run: ## Start the dev server on :8000
	$(PY) manage.py runserver

migrate: install .env ## Apply migrations
	$(PY) manage.py migrate --noinput

seed: install .env ## Load the AP curriculum and demo accounts (idempotent)
	$(PY) manage.py seed_curriculum
	$(PY) manage.py seed_demo

test: install ## Run the test suite
	$(BIN)/pytest

cov: install ## Run the tests with a coverage report
	$(BIN)/pytest --cov --cov-report=term-missing:skip-covered

lint: install ## Lint and check formatting
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

fmt: install ## Auto-fix lint and format
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

check: install ## Django's production checklist, with production-like settings
	DJANGO_DEBUG=0 DJANGO_SECURE=1 DJANGO_SECRET_KEY=$$($(PY) -c 'import secrets;print(secrets.token_urlsafe(50))') \
	  DJANGO_ALLOWED_HOSTS=apelevate.example PAYMENTS_BACKEND=paypal PAYPAL_CLIENT_ID=x PAYPAL_CLIENT_SECRET=x \
	  $(PY) manage.py check --deploy --fail-level WARNING

up: ## Run the app on PostgreSQL with docker compose (http://localhost:8000)
	docker compose up --build

down: ## Stop docker compose and remove its volumes
	docker compose down -v

screenshots: install ## Regenerate docs/screenshots with Playwright
	$(BIN)/pip install --quiet playwright==1.63.0
	$(BIN)/python -m playwright install chromium
	$(PY) scripts/screenshots.py

clean: ## Remove the venv, the SQLite database and caches
	rm -rf $(VENV) db.sqlite3 .pytest_cache .ruff_cache .coverage htmlcov staticfiles
