"""arXiv API client for paper search and retrieval."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

import feedparser
import httpx
from dateutil import parser as date_parser

from models import Author, Paper, SearchResult
from cache_manager import cache_manager
from request_manager import request_manager, RetryConfig

logger = logging.getLogger(__name__)


class ArxivClient:
    """Client for interacting with arXiv API."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(self, max_results_per_request: int = 100):
        self.max_results_per_request = max_results_per_request
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _parse_arxiv_id(self, url: str) -> str:
        """Extract arXiv ID from URL."""
        if "arxiv.org/abs/" in url:
            return url.split("arxiv.org/abs/")[-1]
        return url

    def _parse_authors(self, entry) -> List[Author]:
        """Parse authors from feedparser entry."""
        authors = []
        if hasattr(entry, 'authors'):
            for author in entry.authors:
                authors.append(Author(name=author.name))
        elif hasattr(entry, 'author'):
            authors.append(Author(name=entry.author))
        return authors

    def _parse_categories(self, entry) -> List[str]:
        """Parse categories from feedparser entry."""
        categories = []
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                if hasattr(tag, 'term'):
                    categories.append(tag.term)
        return categories

    def _entry_to_paper(self, entry) -> Paper:
        """Convert feedparser entry to Paper model."""
        arxiv_id = self._parse_arxiv_id(entry.id)

        # Parse dates
        published_date = None
        updated_date = None

        if hasattr(entry, 'published'):
            try:
                published_date = date_parser.parse(entry.published)
            except Exception as e:
                logger.warning(f"Failed to parse published date: {e}")

        if hasattr(entry, 'updated'):
            try:
                updated_date = date_parser.parse(entry.updated)
            except Exception as e:
                logger.warning(f"Failed to parse updated date: {e}")

        # Get PDF URL
        pdf_url = None
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.type == 'application/pdf':
                    pdf_url = link.href
                    break

        return Paper(
            id=arxiv_id,
            title=entry.title.replace('\n', ' ').strip(),
            authors=self._parse_authors(entry),
            abstract=entry.summary.replace('\n', ' ').strip() if hasattr(entry, 'summary') else None,
            published_date=published_date,
            updated_date=updated_date,
            url=entry.id,
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            categories=self._parse_categories(entry),
            source="arxiv",
            source_id=arxiv_id
        )

    async def search(
        self,
        query: str,
        max_results: int = 10,
        start: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "descending"
    ) -> SearchResult:
        """
        Search arXiv for papers.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            start: Starting index for results
            sort_by: Sort criteria ('relevance', 'lastUpdatedDate', 'submittedDate')
            sort_order: Sort order ('ascending', 'descending')
        """
        # Create cache key that includes all parameters
        cache_key_params = f"{query}|{max_results}|{start}|{sort_by}|{sort_order}"

        # Check cache first
        cached_result = cache_manager.get_cached_search_result(cache_key_params, "arxiv")
        if cached_result:
            logger.debug(f"Returning cached arXiv search result for query: {query}")
            return cached_result

        params = {
            "search_query": query,
            "start": start,
            "max_results": min(max_results, self.max_results_per_request),
            "sortBy": sort_by,
            "sortOrder": sort_order
        }

        # Execute request with deduplication and retry logic
        async def _execute_search():
            response = await self._client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            feed = feedparser.parse(response.text)

            if feed.bozo:
                logger.warning(f"Feed parsing warning: {feed.bozo_exception}")

            papers = []
            for entry in feed.entries:
                try:
                    paper = self._entry_to_paper(entry)
                    papers.append(paper)
                    # Cache individual papers too
                    cache_manager.cache_paper(paper.arxiv_id, "arxiv", paper, ttl_hours=48)
                except Exception as e:
                    logger.error(f"Failed to parse paper: {e}")
                    continue

            # Get total results from feed
            total_count = None
            if hasattr(feed, 'feed') and hasattr(feed.feed, 'opensearch_totalresults'):
                try:
                    total_count = int(feed.feed.opensearch_totalresults)
                except (ValueError, AttributeError):
                    pass

            return SearchResult(
                papers=papers,
                total_count=total_count,
                query=query,
                source="arxiv"
            )

        try:
            # Use request manager with arXiv-specific retry config
            retry_config = RetryConfig(
                max_retries=2,
                base_delay=3.0,  # arXiv recommends 3s delays
                max_delay=30.0
            )

            result = await request_manager.deduplicated_request(
                _execute_search,
                endpoint=f"arxiv_search",
                retry_config=retry_config,
                min_interval=3.0  # Respect arXiv rate limits
            )

            # Cache the search result
            cache_manager.cache_search_result(cache_key_params, "arxiv", result, ttl_hours=24)
            logger.debug(f"Cached arXiv search result for query: {query}")

            return result

        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            raise

    async def get_paper_by_id(self, arxiv_id: str) -> Optional[Paper]:
        """Get a specific paper by arXiv ID."""
        # Check cache first
        cached_paper = cache_manager.get_cached_paper(arxiv_id, "arxiv")
        if cached_paper:
            logger.debug(f"Returning cached arXiv paper: {arxiv_id}")
            return cached_paper

        try:
            result = await self.search(f"id:{arxiv_id}", max_results=1)
            paper = result.papers[0] if result.papers else None

            if paper:
                # Cache the paper with longer TTL since paper details don't change often
                cache_manager.cache_paper(arxiv_id, "arxiv", paper, ttl_hours=48)

            return paper
        except Exception as e:
            logger.error(f"Failed to get arXiv paper {arxiv_id}: {e}")
            return None

    async def search_by_author(self, author_name: str, max_results: int = 10) -> SearchResult:
        """Search for papers by author name."""
        query = f"au:{quote(author_name)}"
        return await self.search(query, max_results=max_results)