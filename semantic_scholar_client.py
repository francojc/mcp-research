"""Semantic Scholar API client for paper search and retrieval."""

import asyncio
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

import httpx
from dateutil import parser as date_parser

from models import Author, Paper, SearchResult, Citation
from cache_manager import cache_manager
from request_manager import request_manager, RetryConfig

logger = logging.getLogger(__name__)


class SemanticScholarClient:
    """Client for interacting with Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_headers()
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"User-Agent": "mcp-research/0.1.0"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _parse_authors(self, authors_data: List[Dict[str, Any]]) -> List[Author]:
        """Parse authors from API response."""
        authors = []
        for author_data in authors_data:
            name = author_data.get("name", "")
            if name:
                authors.append(Author(name=name))
        return authors

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        try:
            return date_parser.parse(date_str)
        except Exception as e:
            logger.warning(f"Failed to parse date {date_str}: {e}")
            return None

    def _paper_to_model(self, paper_data: Dict[str, Any]) -> Paper:
        """Convert API paper data to Paper model."""
        paper_id = paper_data.get("paperId", "")

        # Get external IDs
        external_ids = paper_data.get("externalIds", {}) or {}
        arxiv_id = external_ids.get("ArXiv")
        doi = external_ids.get("DOI")

        # Build URLs
        url = paper_data.get("url")
        pdf_url = None
        if paper_data.get("openAccessPdf"):
            pdf_url = paper_data["openAccessPdf"].get("url")

        return Paper(
            id=paper_id,
            title=paper_data.get("title", ""),
            authors=self._parse_authors(paper_data.get("authors", [])),
            abstract=paper_data.get("abstract"),
            published_date=self._parse_date(paper_data.get("publicationDate")),
            url=url,
            pdf_url=pdf_url,
            doi=doi,
            arxiv_id=arxiv_id,
            venue=paper_data.get("venue"),
            citation_count=paper_data.get("citationCount"),
            categories=paper_data.get("fieldsOfStudy", []) or [],
            source="semantic_scholar",
            source_id=paper_id
        )

    async def search(
        self,
        query: str,
        max_results: int = 10,
        offset: int = 0,
        fields: Optional[List[str]] = None
    ) -> SearchResult:
        """
        Search Semantic Scholar for papers.

        Args:
            query: Search query
            max_results: Maximum number of results (max 100 per request)
            offset: Starting offset for results
            fields: Fields to include in response
        """
        if fields is None:
            fields = [
                "paperId", "title", "abstract", "authors", "venue",
                "publicationDate", "citationCount", "fieldsOfStudy",
                "url", "openAccessPdf", "externalIds"
            ]

        # Create cache key that includes all parameters
        cache_key_params = f"{query}|{max_results}|{offset}|{','.join(sorted(fields))}"

        # Check cache first
        cached_result = cache_manager.get_cached_search_result(cache_key_params, "semantic_scholar")
        if cached_result:
            logger.debug(f"Returning cached Semantic Scholar search result for query: {query}")
            return cached_result

        params = {
            "query": query,
            "limit": min(max_results, 100),
            "offset": offset,
            "fields": ",".join(fields)
        }

        # Configure retry and rate limiting for free tier
        retry_config = RetryConfig(
            max_retries=5,
            base_delay=5.0,  # Start with 5 second delay
            max_delay=120.0,  # Max 2 minutes
            exponential_base=2.0
        )

        async def make_search_request():
            response = await self._client.get(
                f"{self.BASE_URL}/paper/search",
                params=params
            )
            response.raise_for_status()
            return response.json()

        try:
            # Use request manager with 3-second minimum interval and exponential backoff
            # Include query parameters in the key for proper deduplication
            data = await request_manager.deduplicated_request(
                make_search_request,
                endpoint=f"semantic_scholar_search_{query}_{max_results}_{offset}",
                retry_config=retry_config,
                min_interval=3.0  # 1 request per 3 seconds
            )

            papers = []

            for paper_data in data.get("data", []):
                try:
                    paper = self._paper_to_model(paper_data)
                    papers.append(paper)
                    # Cache individual papers too
                    cache_manager.cache_paper(paper.source_id, "semantic_scholar", paper, ttl_hours=48)
                except Exception as e:
                    logger.error(f"Failed to parse paper: {e}")
                    continue

            result = SearchResult(
                papers=papers,
                total_count=data.get("total"),
                query=query,
                source="semantic_scholar",
                next_token=data.get("next")
            )

            # Cache the search result
            cache_manager.cache_search_result(cache_key_params, "semantic_scholar", result, ttl_hours=24)
            logger.debug(f"Cached Semantic Scholar search result for query: {query}")

            return result

        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            raise

    async def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """Get a specific paper by Semantic Scholar ID."""
        # Check cache first
        cached_paper = cache_manager.get_cached_paper(paper_id, "semantic_scholar")
        if cached_paper:
            logger.debug(f"Returning cached Semantic Scholar paper: {paper_id}")
            return cached_paper

        fields = [
            "paperId", "title", "abstract", "authors", "venue",
            "publicationDate", "citationCount", "fieldsOfStudy",
            "url", "openAccessPdf", "externalIds"
        ]

        # Configure retry for paper details
        retry_config = RetryConfig(
            max_retries=3,
            base_delay=3.0,
            max_delay=60.0
        )

        async def get_paper_request():
            response = await self._client.get(
                f"{self.BASE_URL}/paper/{paper_id}",
                params={"fields": ",".join(fields)}
            )
            response.raise_for_status()
            return response.json()

        try:
            paper_data = await request_manager.deduplicated_request(
                get_paper_request,
                endpoint=f"semantic_scholar_paper_{paper_id}",
                retry_config=retry_config,
                min_interval=3.0
            )
            paper = self._paper_to_model(paper_data)

            # Cache the paper with longer TTL since paper details don't change often
            cache_manager.cache_paper(paper_id, "semantic_scholar", paper, ttl_hours=48)

            return paper

        except Exception as e:
            logger.error(f"Failed to get Semantic Scholar paper {paper_id}: {e}")
            return None

    async def get_citations(
        self,
        paper_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Paper]:
        """Get papers that cite the given paper."""
        # Create cache key for citations
        cache_key_params = f"{paper_id}|{limit}|{offset}"

        # Check cache first
        cached_citations = cache_manager.get_cached_citations(cache_key_params, "semantic_scholar")
        if cached_citations:
            logger.debug(f"Returning cached citations for paper: {paper_id}")
            return cached_citations

        fields = [
            "paperId", "title", "abstract", "authors", "venue",
            "publicationDate", "citationCount", "fieldsOfStudy",
            "url", "openAccessPdf", "externalIds"
        ]

        # Configure retry for citations
        retry_config = RetryConfig(
            max_retries=3,
            base_delay=3.0,
            max_delay=60.0
        )

        async def get_citations_request():
            response = await self._client.get(
                f"{self.BASE_URL}/paper/{paper_id}/citations",
                params={
                    "fields": ",".join(fields),
                    "limit": limit,
                    "offset": offset
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await request_manager.deduplicated_request(
                get_citations_request,
                endpoint=f"semantic_scholar_citations_{paper_id}_{limit}_{offset}",
                retry_config=retry_config,
                min_interval=3.0
            )
            papers = []

            for citation_data in data.get("data", []):
                try:
                    citing_paper_data = citation_data.get("citingPaper", {})
                    if citing_paper_data:
                        paper = self._paper_to_model(citing_paper_data)
                        papers.append(paper)
                        # Cache individual papers too
                        cache_manager.cache_paper(paper.source_id, "semantic_scholar", paper, ttl_hours=48)
                except Exception as e:
                    logger.error(f"Failed to parse citing paper: {e}")
                    continue

            # Cache the citations
            cache_manager.cache_citations(cache_key_params, "semantic_scholar", papers, ttl_hours=24)
            logger.debug(f"Cached {len(papers)} citations for paper: {paper_id}")

            return papers

        except Exception as e:
            logger.error(f"Failed to get citations for paper {paper_id}: {e}")
            return []

    async def get_references(
        self,
        paper_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Paper]:
        """Get papers referenced by the given paper."""
        fields = [
            "paperId", "title", "abstract", "authors", "venue",
            "publicationDate", "citationCount", "fieldsOfStudy",
            "url", "openAccessPdf", "externalIds"
        ]

        # Configure retry for references
        retry_config = RetryConfig(
            max_retries=3,
            base_delay=3.0,
            max_delay=60.0
        )

        async def get_references_request():
            response = await self._client.get(
                f"{self.BASE_URL}/paper/{paper_id}/references",
                params={
                    "fields": ",".join(fields),
                    "limit": limit,
                    "offset": offset
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await request_manager.deduplicated_request(
                get_references_request,
                endpoint=f"semantic_scholar_references_{paper_id}_{limit}_{offset}",
                retry_config=retry_config,
                min_interval=3.0
            )
            papers = []

            for reference_data in data.get("data", []):
                try:
                    cited_paper_data = reference_data.get("citedPaper", {})
                    if cited_paper_data:
                        paper = self._paper_to_model(cited_paper_data)
                        papers.append(paper)
                except Exception as e:
                    logger.error(f"Failed to parse referenced paper: {e}")
                    continue

            return papers

        except Exception as e:
            logger.error(f"Failed to get references for paper {paper_id}: {e}")
            return []

    async def search_by_author(self, author_name: str, max_results: int = 10) -> SearchResult:
        """Search for papers by author name."""
        query = f"author:{author_name}"
        return await self.search(query, max_results=max_results)