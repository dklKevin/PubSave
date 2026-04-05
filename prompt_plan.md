# Phase 6: Testing/CI

## P0 — Foundation
- [x] Step 1: `ruff format src/ tests/` (9 files)
- [x] Step 2: Upgrade CI — add format check, coverage enforcement, artifact upload

## P1 — High-Impact Coverage
- [x] Step 3: Unit test for `setup_logging` (logging_config.py 27% → 100%)
- [x] Step 4: Integration test for `fetch/{pmid}` endpoint (respx mock)
- [x] Step 5: Integration test for semantic repo (`search_semantic`, `find_unembedded`)

## P2 — Fill Remaining Gaps
- [x] Step 6: Health check failure path test (503 on DB unreachable)
- [x] Step 7: Generic 500 error handler test
- [x] Step 8: CLI `main()` dispatch/help/error tests
- [x] Step 9: CLI branch tests (JSON output, filters, citations, version fallback)

## P3 — Lock It In
- [x] Step 10: Raise `fail_under` to 85 in pyproject.toml

## Previous Plans

### High-Priority Correctness Fixes
- [x] TagRequest tag deduplication
- [x] GIN index on papers.authors
- [x] extract_tag_names unknown type handling
- [x] Extract _TagMixin, op.create_index in migration 004

### Phase 5: API/Config/DevOps
- [x] Rename POST /embed to /embed-all
- [x] Docker healthcheck
- [x] Configurable UVICORN_WORKERS
- [x] entrypoint.sh error handling
- [x] alembic.ini comment
