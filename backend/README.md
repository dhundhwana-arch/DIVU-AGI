# DIVU AI — backend

FastAPI application, Alembic migrations and the pytest suite.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
python manage.py check-config     # validate configuration (never prints secrets)
python manage.py db-upgrade       # apply migrations
python manage.py seed             # roles + demo user (development only)
python manage.py run --reload     # http://localhost:8000/docs
```

## Layout

```
app/
├── core/       config · logging (redaction) · errors (envelope) · ids/time
├── security/   passwords · tokens · encryption · rate_limit · injection · audit
├── db/         engine/session · types · models
├── schemas/    Pydantic v2 contracts
├── services/   auth · users · credentials · audit · system  (all business logic)
├── api/        deps (principal/RBAC) · middleware · routers
└── main.py     application factory, lifespan, CORS, exception handlers, /metrics
migrations/     Alembic (async); one reversible revision per phase
tests/          unit + integration + security + migration tests (SQLite, no services)
manage.py       operator CLI: check-config, seed, create-admin, promote, db-*, run
```

## Conventions

* Routers stay thin — business logic lives in `app/services/`.
* Persistence only through SQLAlchemy models in `app/db/models/`.
* Secrets come from `DIVU_*` environment variables and are redacted from logs.
* PostgreSQL + pgvector in production; SQLite works for development and CI.

## Tests

```bash
pytest -q                       # 62 tests, no external services
pytest --cov=app --cov-report=term-missing
ruff check app tests && ruff format --check app tests
```

Environment variables used by the suite are set in `tests/conftest.py`; each test gets a fresh
SQLite database file.
