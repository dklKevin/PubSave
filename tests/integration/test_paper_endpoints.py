import uuid

import respx
from httpx import AsyncClient, Response

from tests.factories import make_paper_data_unique


def _pubmed_xml(pmid: str) -> str:
    return f"""<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>{pmid}</PMID>
      <Article>
        <Journal><Title>Test Journal</Title></Journal>
        <ArticleTitle>Fetched Paper Title</ArticleTitle>
        <Abstract><AbstractText>Fetched abstract.</AbstractText></Abstract>
        <AuthorList>
          <Author>
            <LastName>Lee</LastName>
            <ForeName>Kevin</ForeName>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


class TestCreatePaperEndpoint:
    async def test_create_paper(self, client: AsyncClient):
        data = make_paper_data_unique()
        response = await client.post("/api/v1/papers", json=data)

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["pmid"] == data["pmid"]
        assert body["data"]["title"] == data["title"]

    async def test_create_duplicate_returns_409(self, client: AsyncClient):
        data = make_paper_data_unique()
        await client.post("/api/v1/papers", json=data)
        response = await client.post("/api/v1/papers", json=data)

        assert response.status_code == 409
        assert response.json()["success"] is False

    async def test_create_invalid_returns_422(self, client: AsyncClient):
        response = await client.post("/api/v1/papers", json={"title": "No PMID"})

        assert response.status_code == 422


class TestGetPaperEndpoint:
    async def test_get_paper(self, client: AsyncClient):
        data = make_paper_data_unique()
        create_resp = await client.post("/api/v1/papers", json=data)
        paper_id = create_resp.json()["data"]["id"]

        response = await client.get(f"/api/v1/papers/{paper_id}")

        assert response.status_code == 200
        assert response.json()["data"]["pmid"] == data["pmid"]

    async def test_get_not_found_returns_404(self, client: AsyncClient):
        import uuid

        response = await client.get(f"/api/v1/papers/{uuid.uuid4()}")
        assert response.status_code == 404


class TestListPapersEndpoint:
    async def test_list_papers(self, client: AsyncClient):
        await client.post("/api/v1/papers", json=make_paper_data_unique())

        response = await client.get("/api/v1/papers")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
        assert body["meta"]["total"] >= 1


class TestUpdatePaperEndpoint:
    async def test_update_paper(self, client: AsyncClient):
        data = make_paper_data_unique()
        create_resp = await client.post("/api/v1/papers", json=data)
        paper_id = create_resp.json()["data"]["id"]

        response = await client.put(f"/api/v1/papers/{paper_id}", json={"title": "Updated Title"})

        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Updated Title"


class TestDeletePaperEndpoint:
    async def test_delete_paper(self, client: AsyncClient):
        data = make_paper_data_unique()
        create_resp = await client.post("/api/v1/papers", json=data)
        paper_id = create_resp.json()["data"]["id"]

        response = await client.delete(f"/api/v1/papers/{paper_id}")
        assert response.status_code == 200

        get_response = await client.get(f"/api/v1/papers/{paper_id}")
        assert get_response.status_code == 404


class TestTagEndpoints:
    async def test_add_and_list_tags(self, client: AsyncClient):
        data = make_paper_data_unique()
        create_resp = await client.post("/api/v1/papers", json=data)
        paper_id = create_resp.json()["data"]["id"]

        tag_resp = await client.post(
            f"/api/v1/papers/{paper_id}/tags", json={"tags": ["ml", "genomics"]}
        )

        assert tag_resp.status_code == 200
        assert "ml" in tag_resp.json()["data"]["tags"]
        assert "genomics" in tag_resp.json()["data"]["tags"]

    async def test_remove_tag(self, client: AsyncClient):
        data = make_paper_data_unique()
        create_resp = await client.post("/api/v1/papers", json=data)
        paper_id = create_resp.json()["data"]["id"]

        await client.post(f"/api/v1/papers/{paper_id}/tags", json={"tags": ["ml", "bio"]})

        remove_resp = await client.delete(f"/api/v1/papers/{paper_id}/tags/ml")
        assert remove_resp.status_code == 200
        assert "ml" not in remove_resp.json()["data"]["tags"]
        assert "bio" in remove_resp.json()["data"]["tags"]

    async def test_list_all_tags(self, client: AsyncClient):
        data = make_paper_data_unique()
        create_resp = await client.post("/api/v1/papers", json=data)
        paper_id = create_resp.json()["data"]["id"]

        await client.post(f"/api/v1/papers/{paper_id}/tags", json={"tags": ["endpoint-test-tag"]})

        response = await client.get("/api/v1/tags")
        assert response.status_code == 200
        body = response.json()
        tag_names = [t["name"] for t in body["data"]]
        assert "endpoint-test-tag" in tag_names
        assert body["meta"]["total"] >= 1
        assert body["meta"]["page"] == 1


class TestSearchEndpoint:
    async def test_search_by_title(self, client: AsyncClient):
        data = make_paper_data_unique(title="Unique Genomics Alpha Study")
        await client.post("/api/v1/papers", json=data)

        response = await client.get("/api/v1/papers/search", params={"q": "Genomics Alpha"})

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] >= 1


class TestCompactQueryParam:
    async def test_list_compact(self, client: AsyncClient):
        data = make_paper_data_unique(
            authors=[{"last_name": "Zhang", "first_name": "Li"}],
        )
        await client.post("/api/v1/papers", json=data)

        response = await client.get("/api/v1/papers", params={"compact": "true"})

        assert response.status_code == 200
        body = response.json()
        papers = body["data"]
        assert len(papers) >= 1
        paper = papers[0]
        assert "authors_short" in paper
        assert "abstract" not in paper
        assert "created_at" not in paper
        assert "updated_at" not in paper

    async def test_get_compact(self, client: AsyncClient):
        data = make_paper_data_unique(
            authors=[
                {"last_name": "Zhang", "first_name": "Li"},
                {"last_name": "Chen", "first_name": "Wei"},
                {"last_name": "Park", "first_name": "Soo"},
            ],
        )
        create_resp = await client.post("/api/v1/papers", json=data)
        paper_id = create_resp.json()["data"]["id"]

        response = await client.get(f"/api/v1/papers/{paper_id}", params={"compact": "true"})

        assert response.status_code == 200
        paper = response.json()["data"]
        assert "et al." in paper["authors_short"]

    async def test_search_compact(self, client: AsyncClient):
        data = make_paper_data_unique(title="Compact Search Test Unique XYZ")
        await client.post("/api/v1/papers", json=data)

        response = await client.get(
            "/api/v1/papers/search", params={"q": "Compact Search Test", "compact": "true"}
        )

        assert response.status_code == 200
        papers = response.json()["data"]
        assert len(papers) >= 1
        assert "authors_short" in papers[0]

    async def test_list_without_compact_returns_full(self, client: AsyncClient):
        data = make_paper_data_unique()
        await client.post("/api/v1/papers", json=data)

        response = await client.get("/api/v1/papers")

        assert response.status_code == 200
        paper = response.json()["data"][0]
        assert "authors" in paper
        assert "created_at" in paper


class TestIdPrefixResolution:
    async def test_id_prefix_returns_matching_paper(self, client: AsyncClient):
        data = make_paper_data_unique()
        create_resp = await client.post("/api/v1/papers", json=data)
        paper_id = create_resp.json()["data"]["id"]
        prefix = paper_id[:8]

        response = await client.get("/api/v1/papers", params={"id_prefix": prefix})

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] >= 1
        ids = [p["id"] for p in body["data"]]
        assert any(pid.startswith(prefix) for pid in ids)

    async def test_id_prefix_no_match_returns_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/papers", params={"id_prefix": "00000000"})

        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    async def test_id_prefix_too_short_returns_422(self, client: AsyncClient):
        response = await client.get("/api/v1/papers", params={"id_prefix": "abc"})

        assert response.status_code == 422


class TestFetchFromPubMed:
    @respx.mock
    async def test_fetch_creates_paper(self, client: AsyncClient):
        pmid = str(uuid.uuid4().int)[:8]
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            return_value=Response(200, text=_pubmed_xml(pmid))
        )

        response = await client.post(f"/api/v1/papers/fetch/{pmid}")

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["pmid"] == pmid
        assert body["data"]["title"] == "Fetched Paper Title"

    @respx.mock
    async def test_fetch_duplicate_returns_409(self, client: AsyncClient):
        pmid = str(uuid.uuid4().int)[:8]
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            return_value=Response(200, text=_pubmed_xml(pmid))
        )

        await client.post(f"/api/v1/papers/fetch/{pmid}")
        response = await client.post(f"/api/v1/papers/fetch/{pmid}")

        assert response.status_code == 409
        assert response.json()["success"] is False
