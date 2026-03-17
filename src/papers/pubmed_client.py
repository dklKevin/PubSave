import logging
import re
import xml.etree.ElementTree as ET

import defusedxml.ElementTree as SafeET
import httpx

from src.exceptions import PubMedFetchError
from src.papers.schemas import AuthorSchema, PaperCreate

logger = logging.getLogger(__name__)

_PMID_RE = re.compile(r"^\d{1,8}$")


class PubMedClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._base_url = base_url
        self._client = client or httpx.AsyncClient(timeout=30)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_paper(self, pmid: str) -> PaperCreate:
        if not _PMID_RE.match(pmid):
            raise PubMedFetchError(pmid, "Invalid PMID format — must be 1-8 digits")

        url = f"{self._base_url}/efetch.fcgi"
        params = {"db": "pubmed", "id": pmid, "rettype": "xml", "retmode": "xml"}

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PubMedFetchError(pmid, f"HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise PubMedFetchError(pmid, str(exc)) from exc

        return self._parse_xml(pmid, response.text)

    def _parse_xml(self, pmid: str, xml_text: str) -> PaperCreate:
        try:
            root = SafeET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise PubMedFetchError(pmid, f"Invalid XML: {exc}") from exc

        article_el = root.find(".//PubmedArticle/MedlineCitation/Article")
        if article_el is None:
            raise PubMedFetchError(pmid, "Article not found in PubMed response")

        title = self._text(article_el, "ArticleTitle", "")
        journal = self._text(article_el, "Journal/Title")
        abstract = self._text(article_el, "Abstract/AbstractText")
        doi = self._find_doi(article_el)
        pub_date = self._parse_date(article_el)
        authors = self._parse_authors(article_el)

        return PaperCreate(
            pmid=pmid,
            title=title,
            authors=authors,
            abstract=abstract,
            journal=journal,
            publication_date=pub_date,
            doi=doi,
        )

    def _text(self, parent: ET.Element, path: str, default: str | None = None) -> str | None:
        el = parent.find(path)
        if el is not None and el.text:
            return el.text.strip()
        return default

    def _find_doi(self, article_el: ET.Element) -> str | None:
        for eid in article_el.findall("ELocationID"):
            if eid.get("EIdType") == "doi" and eid.text:
                return eid.text.strip()
        return None

    def _parse_date(self, article_el: ET.Element) -> str | None:
        date_el = article_el.find("ArticleDate")
        if date_el is None:
            return None

        year = self._text(date_el, "Year")
        month = self._text(date_el, "Month")
        day = self._text(date_el, "Day")

        if not year:
            return None

        parts = [year]
        if month:
            parts.append(month.zfill(2))
        if day:
            parts.append(day.zfill(2))

        return "-".join(parts)

    def _parse_authors(self, article_el: ET.Element) -> list[AuthorSchema]:
        authors = []
        for author_el in article_el.findall("AuthorList/Author"):
            last = self._text(author_el, "LastName")
            first = self._text(author_el, "ForeName")
            if not last or not first:
                continue

            affiliation = self._text(author_el, "AffiliationInfo/Affiliation")
            authors.append(AuthorSchema(last_name=last, first_name=first, affiliation=affiliation))

        return authors
