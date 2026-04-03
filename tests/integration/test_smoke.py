"""Smoke test — exercises every API endpoint and major function path.

Covers routes and behaviors not reached by the focused unit/integration tests:
health check, semantic search 503, ask 503, embed-all, error handler paths,
compact query params on search, and the full CRUD + tag lifecycle.
"""

from httpx import AsyncClient

from tests.factories import make_paper_data_unique


class TestHealthEndpoint:
    async def test_health_returns_healthy(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "healthy"


class TestSemanticSearch503:
    """Semantic search returns 503 when no embedder is configured."""

    async def test_semantic_search_without_embedder(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/papers/search/semantic", params={"q": "gene therapy"}
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["success"] is False
        assert "unavailable" in body["error"].lower() or "RAG" in body["error"]


class TestAsk503:
    """Ask endpoint returns 503 when no embedder/LLM configured."""

    async def test_ask_without_rag(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/ask", json={"question": "What is gene therapy?"}
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["success"] is False


class TestEmbedAllEndpoint:
    async def test_embed_all_returns_zero_without_embedder(self, client: AsyncClient):
        resp = await client.post("/api/v1/papers/embed")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["embedded"] == 0


class TestFullPaperLifecycle:
    """End-to-end: create -> get -> update -> search -> tag -> untag -> delete."""

    async def test_full_lifecycle(self, client: AsyncClient):
        # Create
        data = make_paper_data_unique(
            title="Smoke Test Lifecycle Paper",
            authors=[
                {"last_name": "Smoke", "first_name": "Test"},
                {"last_name": "Runner", "first_name": "Quick"},
            ],
        )
        create_resp = await client.post("/api/v1/papers", json=data)
        assert create_resp.status_code == 201
        paper_id = create_resp.json()["data"]["id"]

        # Get full
        get_resp = await client.get(f"/api/v1/papers/{paper_id}")
        assert get_resp.status_code == 200
        paper = get_resp.json()["data"]
        assert paper["title"] == "Smoke Test Lifecycle Paper"
        assert "created_at" in paper
        assert "updated_at" in paper

        # Get compact
        compact_resp = await client.get(
            f"/api/v1/papers/{paper_id}", params={"compact": "true"}
        )
        assert compact_resp.status_code == 200
        compact = compact_resp.json()["data"]
        assert "authors_short" in compact
        assert "Smoke T" in compact["authors_short"]
        assert "abstract" not in compact

        # Update
        update_resp = await client.put(
            f"/api/v1/papers/{paper_id}",
            json={"title": "Updated Smoke Test"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["title"] == "Updated Smoke Test"

        # Search by keyword
        search_resp = await client.get(
            "/api/v1/papers/search", params={"q": "Updated Smoke"}
        )
        assert search_resp.status_code == 200
        assert search_resp.json()["meta"]["total"] >= 1

        # Search compact
        search_compact = await client.get(
            "/api/v1/papers/search",
            params={"q": "Updated Smoke", "compact": "true"},
        )
        assert search_compact.status_code == 200
        results = search_compact.json()["data"]
        assert len(results) >= 1
        assert "authors_short" in results[0]

        # Search by author
        author_resp = await client.get(
            "/api/v1/papers/search", params={"author": "Smoke"}
        )
        assert author_resp.status_code == 200
        assert author_resp.json()["meta"]["total"] >= 1

        # Tag
        tag_resp = await client.post(
            f"/api/v1/papers/{paper_id}/tags",
            json={"tags": ["smoke-test", "lifecycle"]},
        )
        assert tag_resp.status_code == 200
        assert "smoke-test" in tag_resp.json()["data"]["tags"]

        # List tags
        tags_resp = await client.get("/api/v1/tags")
        assert tags_resp.status_code == 200
        tag_names = [t["name"] for t in tags_resp.json()["data"]]
        assert "smoke-test" in tag_names

        # Search by tag
        tag_search = await client.get(
            "/api/v1/papers/search", params={"tag": "smoke-test"}
        )
        assert tag_search.status_code == 200
        assert tag_search.json()["meta"]["total"] >= 1

        # Untag
        untag_resp = await client.delete(
            f"/api/v1/papers/{paper_id}/tags/smoke-test"
        )
        assert untag_resp.status_code == 200
        assert "smoke-test" not in untag_resp.json()["data"]["tags"]

        # Delete
        del_resp = await client.delete(f"/api/v1/papers/{paper_id}")
        assert del_resp.status_code == 200

        # Verify deleted
        gone_resp = await client.get(f"/api/v1/papers/{paper_id}")
        assert gone_resp.status_code == 404


class TestErrorHandlerPaths:
    async def test_404_paper_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/papers/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
        body = resp.json()
        assert body["success"] is False
        assert "not found" in body["error"].lower()

    async def test_409_duplicate_pmid(self, client: AsyncClient):
        data = make_paper_data_unique()
        await client.post("/api/v1/papers", json=data)
        resp = await client.post("/api/v1/papers", json=data)
        assert resp.status_code == 409
        assert resp.json()["success"] is False

    async def test_422_validation_error(self, client: AsyncClient):
        resp = await client.post("/api/v1/papers", json={"title": "Missing PMID"})
        assert resp.status_code == 422

    async def test_tag_not_found(self, client: AsyncClient):
        data = make_paper_data_unique()
        create_resp = await client.post("/api/v1/papers", json=data)
        paper_id = create_resp.json()["data"]["id"]

        resp = await client.delete(f"/api/v1/papers/{paper_id}/tags/nonexistent")
        assert resp.status_code == 404

    async def test_list_papers_pagination(self, client: AsyncClient):
        resp = await client.get("/api/v1/papers", params={"page": 1, "limit": 5})
        assert resp.status_code == 200
        assert resp.json()["meta"]["limit"] == 5

    async def test_embed_endpoint_position(self, client: AsyncClient):
        """POST /embed must not be captured by /{paper_id} route."""
        resp = await client.post("/api/v1/papers/embed")
        assert resp.status_code == 200
