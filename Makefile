# DIVU AI — developer entry points
# Run `make help` for the full list.

PYTHON ?= python3
VENV ?= .venv
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000
PREVIEW_HOST ?= 0.0.0.0

.PHONY: help setup dev dev-backend dev-frontend test coverage lint format \
        migrate revision seed create-admin check-config docker-up docker-down clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Create virtualenvs and install backend + frontend dependencies
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r backend/requirements-dev.txt
	cd frontend && npm install
	@echo "\nNext: cp .env.example .env (optional) then 'make dev'"

dev-backend: ## Run the FastAPI API with auto-reload
	cd backend && $(CURDIR)/$(VENV)/bin/python manage.py run --host $(PREVIEW_HOST) --port $(BACKEND_PORT) --reload

dev-frontend: ## Run the Next.js web app
	cd frontend && npm run dev -- --hostname $(PREVIEW_HOST) --port $(FRONTEND_PORT)

dev: ## Run both (use two terminals / processes)
	@echo "Start 'make dev-backend' and 'make dev-frontend' in separate shells."

test: ## Run the backend test suite
	cd backend && $(CURDIR)/$(VENV)/bin/python -m pytest -q

coverage: ## Run tests with a coverage report
	cd backend && $(CURDIR)/$(VENV)/bin/python -m pytest --cov=app --cov-report=term-missing

lint: ## Lint backend (ruff) and frontend (eslint + tsc)
	cd backend && $(CURDIR)/$(VENV)/bin/ruff check app tests
	cd backend && $(CURDIR)/$(VENV)/bin/ruff format --check app tests
	cd frontend && npx tsc --noEmit

format: ## Auto-format backend code
	cd backend && $(CURDIR)/$(VENV)/bin/ruff check --fix app tests
	cd backend && $(CURDIR)/$(VENV)/bin/ruff format app tests

check-config: ## Validate configuration (no secrets printed)
	cd backend && $(CURDIR)/$(VENV)/bin/python manage.py check-config

migrate: ## Apply database migrations
	cd backend && $(CURDIR)/$(VENV)/bin/python manage.py db-upgrade

revision: ## Autogenerate a migration: make revision m="message"
	cd backend && $(CURDIR)/$(VENV)/bin/python manage.py db-revision "$(m)"

seed: ## Seed roles and a demo user (development only)
	cd backend && $(CURDIR)/$(VENV)/bin/python manage.py seed

create-admin: ## Create an admin: make create-admin e=you@example.com
	cd backend && $(CURDIR)/$(VENV)/bin/python manage.py create-admin --email "$(e)"

docker-up: ## Start Postgres+pgvector, Redis, MinIO, API and web
	docker compose up --build

docker-down: ## Stop the compose stack
	docker compose down

clean: ## Remove caches and local data
	rm -rf backend/.data backend/.pytest_cache backend/.ruff_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
