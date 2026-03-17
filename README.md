# PubSave

A personal API for bookmarking and organizing research papers from PubMed. Give it a PMID, it fetches the metadata, saves it to Postgres, and lets you tag and search through your collection.

The whole stack runs with one command:

```bash
docker compose up
```

## Quick start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for the CLI)

### Install and run

```bash
git clone https://github.com/dklKevin/PubSave.git
cd PubSave
cp .env.example .env
docker compose up

# Install the CLI
pip install -e .
```

The API runs at `http://localhost:8000`. Migrations run automatically on startup.

## CLI

PubSave ships with a terminal CLI. Every command talks to the API, so `docker compose up` must be running.

```bash
# Save a paper from PubMed
pubsave fetch 33057194

# List your papers
pubsave ls

# View a specific paper (6+ char ID prefix works)
pubsave get a1b2c3

# Search by keyword, author, or tag
pubsave search microbiome
pubsave search -a Zhang
pubsave search -t genetics

# Tag a paper
pubsave tag a1b2c3 genetics to-read

# Remove a tag
pubsave untag a1b2c3 to-read

# Delete a paper (with confirmation)
pubsave rm a1b2c3

# List all tags
pubsave tags
```

### CLI options

| Flag | Description |
|------|-------------|
| `--json` | Raw JSON output |
| `--full` | Full details (skip compact mode) |
| `--page N` | Pagination page |
| `--limit N` | Results per page |

Short IDs work everywhere. Type the first 6+ characters of any paper's UUID instead of the full thing.

Set `PUBSAVE_URL` to point at a different server (defaults to `http://localhost:8000`).

## API endpoints

The CLI wraps these REST endpoints. You can also call them directly with curl or httpie.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/papers/fetch/{pmid}` | Fetch a paper from PubMed by PMID and save it |
| `POST` | `/api/v1/papers` | Save a paper manually |
| `GET` | `/api/v1/papers` | List all saved papers (paginated) |
| `GET` | `/api/v1/papers/search` | Search by keyword, author, tag, or PMID |
| `GET` | `/api/v1/papers/{id}` | Get a single paper |
| `PUT` | `/api/v1/papers/{id}` | Update paper metadata |
| `DELETE` | `/api/v1/papers/{id}` | Remove a paper |
| `POST` | `/api/v1/papers/{id}/tags` | Add tags to a paper |
| `DELETE` | `/api/v1/papers/{id}/tags/{name}` | Remove a tag from a paper |
| `GET` | `/api/v1/tags` | List all tags (paginated) |
| `GET` | `/health` | Health check (API + database) |

All list endpoints accept `?compact=true` to get shorter responses with `authors_short` instead of the full authors array.

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌────────────┐
│  pubsave │────>│   FastAPI    │────>│ PostgreSQL │
│   (CLI)  │<────│  (async)     │<────│   (Docker) │
└──────────┘     └──────┬───────┘     └────────────┘
                        │
                        v
                 ┌──────────────┐
                 │  PubMed API  │
                 │ (E-utilities)│
                 └──────────────┘
```

### Project structure

```
src/
├── main.py              # App factory, lifespan, router registration
├── cli.py               # Terminal CLI (pubsave command)
├── config.py            # Pydantic Settings (env-based configuration)
├── database.py          # Async SQLAlchemy engine and session factory
├── dependencies.py      # FastAPI dependency injection
├── exceptions.py        # Custom exception hierarchy
├── logging_config.py    # Structured logging setup
├── health/
│   └── router.py        # Health check endpoint (API + DB)
├── middleware/
│   └── error_handler.py # Maps exceptions to HTTP responses
└── papers/
    ├── models.py        # SQLAlchemy ORM models (Paper, Tag)
    ├── schemas.py       # Pydantic validation schemas
    ├── repository.py    # Database queries (repository pattern)
    ├── service.py       # Business logic layer
    ├── router.py        # Paper API endpoints
    ├── tag_router.py    # Tag API endpoints
    └── pubmed_client.py # PubMed XML fetch and parse
```

### Design decisions

- **Repository pattern** -- database queries are isolated from business logic
- **Service layer** -- orchestrates repositories and external clients
- **Dependency injection** -- FastAPI's `Depends()` wires everything together
- **Immutable schemas** -- all Pydantic models use `frozen=True`
- **Async everywhere** -- SQLAlchemy 2.0 async with asyncpg driver
- **Multi-stage Docker build** -- smaller production image
- **Fail-fast configuration** -- missing env vars crash on startup, not at runtime
- **LIKE wildcard escaping** -- search queries sanitize `%` and `_` to prevent injection
- **ANSI sanitization** -- CLI strips escape sequences from API responses

## Testing

95 tests across two layers:

| Layer | Tests | What's covered |
|-------|------:|----------------|
| Unit | 51 | Schema validation, service logic, PubMed XML parsing, CLI helpers, compact response |
| Integration | 44 | Repository queries, API endpoints, compact param, tag operations, ID prefix resolution (real Postgres) |

Integration tests run against a real PostgreSQL instance via [testcontainers](https://testcontainers-python.readthedocs.io/) -- no SQLite mocks.

### Run tests

```bash
# Requires Python 3.12+ and Docker (for testcontainers)
pip install -e ".[dev]"
pytest
```

## Tech stack

| Component | Technology |
|-----------|------------|
| API framework | FastAPI (async) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (asyncpg) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| HTTP client | httpx (async for API, sync for CLI) |
| XML parsing | defusedxml (XXE-safe) |
| Container | Docker + Docker Compose |
| Testing | pytest + testcontainers |
| Linting | Ruff |
