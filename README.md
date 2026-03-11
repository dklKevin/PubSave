# PubSave

A personal API for bookmarking and organizing research papers from PubMed. Give it a PMID, it fetches the metadata, saves it to Postgres, and lets you tag and search through your collection.

The whole stack runs with one command:

```bash
docker compose up
```

## What it does

PubSave connects to the [PubMed E-utilities API](https://www.ncbi.nlm.nih.gov/books/NBK25501/) to pull paper metadata — title, authors, abstract, journal, DOI, and publication date — then stores it in a PostgreSQL database with full tagging and search support.

### API endpoints

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

### Example workflow

```bash
# Fetch a paper from PubMed
curl -X POST http://localhost:8000/api/v1/papers/fetch/33057194

# Tag it
curl -X POST http://localhost:8000/api/v1/papers/{id}/tags \
  -H "Content-Type: application/json" \
  -d '{"tags": ["genetics", "to-read"]}'

# Search by tag
curl "http://localhost:8000/api/v1/papers/search?tag=genetics"

# Search by keyword across titles and abstracts
curl "http://localhost:8000/api/v1/papers/search?q=microbiome"

# Search by author
curl "http://localhost:8000/api/v1/papers/search?author=Zhang"

# List everything
curl http://localhost:8000/api/v1/papers
```

## Setup

### Prerequisites

- Docker and Docker Compose

### Run

```bash
# Clone the repo
git clone https://github.com/your-username/PubSave.git
cd PubSave

# Create your .env file
cp .env.example .env
# Edit .env with your preferred database credentials

# Start everything
docker compose up
```

The API will be available at `http://localhost:8000`. Database migrations run automatically on startup.

### Run tests (local development)

```bash
# Requires Python 3.12+ and Docker (for testcontainers)
pip install -e ".[dev]"
pytest
```

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌────────────┐
│  Client  │────>│   FastAPI    │────>│ PostgreSQL │
│ (curl)   │<────│  (async)     │<────│   (Docker) │
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

- **Repository pattern** — database queries are isolated from business logic
- **Service layer** — orchestrates repositories and external clients
- **Dependency injection** — FastAPI's `Depends()` wires everything together
- **Immutable schemas** — all Pydantic models use `frozen=True`
- **Async everywhere** — SQLAlchemy 2.0 async with asyncpg driver
- **Multi-stage Docker build** — smaller production image
- **Fail-fast configuration** — missing env vars crash on startup, not at runtime

## Testing

64 tests across three layers:

| Layer | Tests | What's covered |
|-------|------:|----------------|
| Unit | 35 | Schema validation, service logic, PubMed XML parsing |
| Integration | 29 | Repository queries, API endpoints (real Postgres) |

```
Coverage: 92%
```

Integration tests run against a real PostgreSQL instance via [testcontainers](https://testcontainers-python.readthedocs.io/) — no SQLite mocks.

## Tech stack

| Component | Technology |
|-----------|------------|
| API framework | FastAPI (async) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (asyncpg) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| HTTP client | httpx (async) |
| XML parsing | defusedxml (XXE-safe) |
| Container | Docker + Docker Compose |
| Testing | pytest + testcontainers |
| Linting | Ruff |

## What I learned

### Docker as project infrastructure
Docker Compose isn't a separate skill to learn — it's how the project runs. One `docker-compose.yml` defines both services, wires networking, manages volumes, and gates startup with healthchecks. The Dockerfile, entrypoint script, and compose file become as normal as `pyproject.toml`.

### Test-driven development in practice
Every layer was built test-first: write a failing test, implement just enough to pass it, then refactor. This caught real bugs early — JSONB author search required `cast(Paper.authors, String)` instead of `.cast(str)`, which only surfaced when tests hit a real Postgres instance.

### Async Python from request to database
The entire request path is async: FastAPI handles the request, httpx fetches from PubMed, SQLAlchemy issues queries through asyncpg. Understanding how `async/await` flows through middleware, dependency injection, and database sessions was a core part of the project.

### Repository pattern and layered architecture
Separating database queries (repository), business logic (service), and HTTP handling (router) into distinct layers made each piece independently testable. Unit tests mock the repository, integration tests use a real database — same service code, different test strategies.

### Security as a habit, not an afterthought
A code review caught three critical issues: XML External Entity (XXE) vulnerability in PubMed parsing, hardcoded password fallbacks in Docker config, and missing input validation on PMIDs. Fixing these led to `defusedxml`, fail-fast environment variables, and regex validation — patterns that apply to any project.

### Pydantic as a validation boundary
Frozen Pydantic models with field validators act as a trust boundary between external data and internal logic. Tag normalization, PMID format checks, and ORM-to-response conversion all happen at the schema level — not scattered through router code.
