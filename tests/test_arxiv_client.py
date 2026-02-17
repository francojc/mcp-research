"""Tests for ArXiv API client."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime

import feedparser

from arxiv_client import ArxivClient
from models import Paper, SearchResult


class TestArxivClient:
    """Test cases for ArxivClient."""

    @pytest.fixture
    def client(self):
        """Create ArxivClient instance for testing."""
        return ArxivClient()

    # -- Unit tests for sync helpers --

    def test_parse_arxiv_id_from_url(self, client):
        """Extract arXiv ID from standard URL formats."""
        cases = [
            (
                "http://arxiv.org/abs/2306.12345v1",
                "2306.12345v1",
            ),
            (
                "http://arxiv.org/abs/2306.12345",
                "2306.12345",
            ),
            (
                "https://arxiv.org/abs/1234.5678v2",
                "1234.5678v2",
            ),
        ]
        for url, expected in cases:
            assert client._parse_arxiv_id(url) == expected

    def test_parse_arxiv_id_passthrough(self, client):
        """Non-URL strings are returned as-is."""
        assert client._parse_arxiv_id("2306.12345v1") == "2306.12345v1"
        assert client._parse_arxiv_id("some-id") == "some-id"

    def test_entry_to_paper(self, client, mock_arxiv_response_text):
        """feedparser entry converts to Paper model."""
        feed = feedparser.parse(mock_arxiv_response_text)
        assert len(feed.entries) == 1

        paper = client._entry_to_paper(feed.entries[0])

        assert isinstance(paper, Paper)
        assert paper.title == "Test Machine Learning Paper"
        assert paper.abstract == (
            "This is a test abstract about machine learning."
        )
        assert paper.arxiv_id == "2306.12345v1"
        assert paper.source == "arxiv"
        assert paper.source_id == "2306.12345v1"
        assert len(paper.authors) == 1
        assert paper.authors[0].name == "Test Author"
        assert "cs.LG" in paper.categories
        assert "stat.ML" in paper.categories
        assert paper.published_date is not None

    def test_parse_authors_multiple(self, client, mock_arxiv_response_text):
        """Author parsing handles feed entries."""
        feed = feedparser.parse(mock_arxiv_response_text)
        entry = feed.entries[0]
        authors = client._parse_authors(entry)
        assert len(authors) == 1
        assert authors[0].name == "Test Author"

    def test_parse_categories(self, client, mock_arxiv_response_text):
        """Category parsing from feed entry."""
        feed = feedparser.parse(mock_arxiv_response_text)
        entry = feed.entries[0]
        categories = client._parse_categories(entry)
        assert "cs.LG" in categories
        assert "stat.ML" in categories

    # -- Async tests using mocked request_manager --

    @pytest.mark.asyncio
    async def test_search_success(
        self, client, mock_arxiv_response_text
    ):
        """Successful search returns parsed papers."""
        with patch(
            "arxiv_client.request_manager"
        ) as mock_rm, patch(
            "arxiv_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_search_result.return_value = None

            feed = feedparser.parse(mock_arxiv_response_text)
            papers = []
            for entry in feed.entries:
                papers.append(client._entry_to_paper(entry))

            expected_result = SearchResult(
                papers=papers,
                total_count=1,
                query="machine learning",
                source="arxiv",
            )

            async def fake_request(request_func, **kwargs):
                return expected_result

            mock_rm.deduplicated_request = AsyncMock(
                side_effect=fake_request
            )

            result = await client.search(
                "machine learning", max_results=1
            )

            assert isinstance(result, SearchResult)
            assert result.source == "arxiv"
            assert len(result.papers) == 1
            assert result.papers[0].title == "Test Machine Learning Paper"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, client):
        """Search with no results returns empty SearchResult."""
        with patch(
            "arxiv_client.request_manager"
        ) as mock_rm, patch(
            "arxiv_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_search_result.return_value = None

            empty_result = SearchResult(
                papers=[],
                total_count=0,
                query="nonexistent",
                source="arxiv",
            )

            async def fake_request(request_func, **kwargs):
                return empty_result

            mock_rm.deduplicated_request = AsyncMock(
                side_effect=fake_request
            )

            result = await client.search("nonexistent topic")
            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0

    @pytest.mark.asyncio
    async def test_search_raises_on_failure(self, client):
        """Search propagates exceptions."""
        with patch(
            "arxiv_client.request_manager"
        ) as mock_rm, patch(
            "arxiv_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_search_result.return_value = None
            mock_rm.deduplicated_request = AsyncMock(
                side_effect=Exception("HTTP 500")
            )

            with pytest.raises(Exception, match="HTTP 500"):
                await client.search("test query")

    @pytest.mark.asyncio
    async def test_search_returns_cached(self, client):
        """Cached result is returned without network request."""
        cached = SearchResult(
            papers=[],
            total_count=0,
            query="cached",
            source="arxiv",
        )
        with patch("arxiv_client.cache_manager") as mock_cm:
            mock_cm.get_cached_search_result.return_value = cached

            result = await client.search("cached")
            assert result is cached

    @pytest.mark.asyncio
    async def test_get_paper_by_id_success(self, client):
        """get_paper_by_id returns Paper when found."""
        paper = Paper(
            id="2306.12345",
            title="Found Paper",
            authors=[],
            source="arxiv",
            source_id="2306.12345",
            arxiv_id="2306.12345",
        )
        found_result = SearchResult(
            papers=[paper],
            total_count=1,
            query="id:2306.12345",
            source="arxiv",
        )
        with patch.object(
            client, "search", new_callable=AsyncMock
        ) as mock_search, patch(
            "arxiv_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_paper.return_value = None
            mock_search.return_value = found_result

            result = await client.get_paper_by_id("2306.12345")
            assert result is not None
            assert result.title == "Found Paper"

    @pytest.mark.asyncio
    async def test_get_paper_by_id_not_found(self, client):
        """get_paper_by_id returns None when not found."""
        empty_result = SearchResult(
            papers=[],
            total_count=0,
            query="id:nonexistent",
            source="arxiv",
        )
        with patch.object(
            client, "search", new_callable=AsyncMock
        ) as mock_search, patch(
            "arxiv_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_paper.return_value = None
            mock_search.return_value = empty_result

            result = await client.get_paper_by_id("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_search_by_author(self, client):
        """search_by_author delegates to search with au: prefix."""
        with patch.object(
            client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = SearchResult(
                papers=[],
                total_count=0,
                query="au:Test%20Author",
                source="arxiv",
            )
            await client.search_by_author("Test Author")

            # Should have been called with au: prefix
            call_args = mock_search.call_args
            assert call_args[0][0].startswith("au:")
