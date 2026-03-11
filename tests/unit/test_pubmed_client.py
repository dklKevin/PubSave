import httpx
import pytest
import respx

from src.exceptions import PubMedFetchError
from src.papers.pubmed_client import PubMedClient

SAMPLE_XML = """<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <Journal>
          <Title>Nature Genetics</Title>
        </Journal>
        <ArticleTitle>A sample study on genomics</ArticleTitle>
        <Abstract>
          <AbstractText>This is the abstract of the paper.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
            <AffiliationInfo>
              <Affiliation>MIT</Affiliation>
            </AffiliationInfo>
          </Author>
          <Author>
            <LastName>Doe</LastName>
            <ForeName>Jane</ForeName>
          </Author>
        </AuthorList>
        <ArticleDate>
          <Year>2025</Year>
          <Month>03</Month>
          <Day>15</Day>
        </ArticleDate>
        <ELocationID EIdType="doi">10.1000/test.123</ELocationID>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""

EMPTY_XML = """<?xml version="1.0" ?>
<PubmedArticleSet></PubmedArticleSet>"""


@pytest.fixture
def client():
    return PubMedClient(base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils")


class TestPubMedClientFetch:
    @respx.mock
    async def test_fetch_success(self, client):
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML)
        )

        paper = await client.fetch_paper("12345678")
        assert paper.pmid == "12345678"
        assert paper.title == "A sample study on genomics"
        assert paper.journal == "Nature Genetics"
        assert paper.abstract == "This is the abstract of the paper."
        assert len(paper.authors) == 2
        assert paper.authors[0].last_name == "Smith"
        assert paper.authors[0].first_name == "John"
        assert paper.authors[0].affiliation == "MIT"
        assert paper.doi == "10.1000/test.123"

    @respx.mock
    async def test_fetch_not_found(self, client):
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            return_value=httpx.Response(200, text=EMPTY_XML)
        )

        with pytest.raises(PubMedFetchError, match="not found"):
            await client.fetch_paper("99999999")

    @respx.mock
    async def test_fetch_network_error(self, client):
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(PubMedFetchError, match="Connection"):
            await client.fetch_paper("12345678")

    @respx.mock
    async def test_fetch_http_error(self, client):
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(PubMedFetchError):
            await client.fetch_paper("12345678")

    @respx.mock
    async def test_fetch_malformed_xml(self, client):
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            return_value=httpx.Response(200, text="<not>valid</xml>")
        )

        with pytest.raises(PubMedFetchError):
            await client.fetch_paper("12345678")
