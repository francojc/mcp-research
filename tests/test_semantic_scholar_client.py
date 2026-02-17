"""Tests for Semantic Scholar API client."""

import pytest
from unittest.mock import AsyncMock, patch, Mock, MagicMock
from datetime import datetime

from semantic_scholar_client import SemanticScholarClient
from models import Paper, Author, SearchResult


class TestSemanticScholarClient:
    """Test cases for SemanticScholarClient."""

    @pytest.fixture
    def client(self):
        """Create SemanticScholarClient instance for testing."""
        return SemanticScholarClient(api_key="test-api-key")

    # -- Unit tests for sync helpers (no mocking needed) --

    def test_get_headers_with_api_key(self, client):
        """Headers include x-api-key when an API key is set."""
        headers = client._get_headers()
        assert headers["x-api-key"] == "test-api-key"
        assert "User-Agent" in headers

    def test_get_headers_without_api_key(self):
        """Headers omit x-api-key when no key is provided."""
        client = SemanticScholarClient(api_key=None)
        # Clear env var if set
        with patch.dict("os.environ", {}, clear=True):
            client_no_key = SemanticScholarClient()
        headers = client_no_key._get_headers()
        assert "x-api-key" not in headers

    def test_parse_authors(self, client):
        """Author parsing extracts names correctly."""
        authors_data = [
            {"name": "Alice", "authorId": "1"},
            {"name": "Bob", "authorId": "2"},
            {"name": ""},  # empty name is skipped
        ]
        authors = client._parse_authors(authors_data)
        assert len(authors) == 2
        assert authors[0].name == "Alice"
        assert authors[1].name == "Bob"

    def test_parse_date_valid(self, client):
        """Valid date string is parsed to datetime."""
        dt = client._parse_date("2023-06-15")
        assert dt is not None
        assert dt.year == 2023
        assert dt.month == 6
        assert dt.day == 15

    def test_parse_date_none(self, client):
        """None/empty date returns None."""
        assert client._parse_date(None) is None
        assert client._parse_date("") is None

    def test_parse_date_invalid(self, client):
        """Invalid date string returns None."""
        assert client._parse_date("not-a-date") is None

    def test_paper_to_model_complete(self, client):
        """Complete paper data converts to Paper model."""
        data = {
            "paperId": "abc123",
            "title": "Test Paper",
            "abstract": "An abstract.",
            "venue": "ICML",
            "publicationDate": "2023-06-15",
            "authors": [{"name": "Author One"}],
            "citationCount": 50,
            "externalIds": {"DOI": "10.1234/test", "ArXiv": "2306.99999"},
            "url": "https://semanticscholar.org/paper/abc123",
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            "fieldsOfStudy": ["Computer Science"],
        }
        paper = client._paper_to_model(data)

        assert paper.id == "abc123"
        assert paper.title == "Test Paper"
        assert paper.abstract == "An abstract."
        assert paper.venue == "ICML"
        assert paper.citation_count == 50
        assert paper.doi == "10.1234/test"
        assert paper.arxiv_id == "2306.99999"
        assert paper.pdf_url == "https://example.com/paper.pdf"
        assert paper.source == "semantic_scholar"
        assert paper.source_id == "abc123"
        assert "Computer Science" in paper.categories

    def test_paper_to_model_minimal(self, client):
        """Minimal paper data (just ID and title) converts."""
        data = {"paperId": "min123", "title": "Minimal"}
        paper = client._paper_to_model(data)

        assert paper.id == "min123"
        assert paper.title == "Minimal"
        assert paper.abstract is None
        assert paper.doi is None
        assert paper.arxiv_id is None
        assert paper.citation_count is None
        assert len(paper.authors) == 0
        assert paper.categories == []

    def test_paper_to_model_missing_id(self, client):
        """Paper with empty ID still converts (ID defaults to '')."""
        data = {"title": "No ID"}
        paper = client._paper_to_model(data)
        assert paper.id == ""

    # -- Async tests using mocked request_manager --

    @pytest.mark.asyncio
    async def test_search_success(
        self, client, mock_semantic_scholar_response
    ):
        """Successful search returns papers."""
        with patch(
            "semantic_scholar_client.request_manager"
        ) as mock_rm, patch(
            "semantic_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_search_result.return_value = None

            async def fake_request(request_func, **kwargs):
                return mock_semantic_scholar_response

            mock_rm.deduplicated_request = AsyncMock(
                side_effect=fake_request
            )

            result = await client.search("machine learning", max_results=1)

            assert isinstance(result, SearchResult)
            assert result.source == "semantic_scholar"
            assert result.query == "machine learning"
            assert len(result.papers) == 1

            paper = result.papers[0]
            assert paper.title == "Test Semantic Scholar Paper"
            assert paper.source == "semantic_scholar"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, client):
        """Search returning no data yields empty paper list."""
        with patch(
            "semantic_scholar_client.request_manager"
        ) as mock_rm, patch(
            "semantic_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_search_result.return_value = None

            async def fake_request(request_func, **kwargs):
                return {"total": 0, "data": []}

            mock_rm.deduplicated_request = AsyncMock(
                side_effect=fake_request
            )

            result = await client.search("nonexistent")
            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_search_raises_on_failure(self, client):
        """Search propagates exceptions from request_manager."""
        with patch(
            "semantic_scholar_client.request_manager"
        ) as mock_rm, patch(
            "semantic_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_search_result.return_value = None
            mock_rm.deduplicated_request = AsyncMock(
                side_effect=Exception("Rate limited")
            )

            with pytest.raises(Exception, match="Rate limited"):
                await client.search("test query")

    @pytest.mark.asyncio
    async def test_search_returns_cached_result(self, client):
        """Search returns cached result without hitting the network."""
        cached = SearchResult(
            papers=[],
            total_count=0,
            query="cached",
            source="semantic_scholar",
        )
        with patch(
            "semantic_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_search_result.return_value = cached

            result = await client.search("cached")
            assert result is cached

    @pytest.mark.asyncio
    async def test_get_paper_by_id_success(self, client):
        """get_paper_by_id returns a Paper on success."""
        paper_data = {
            "paperId": "test-id",
            "title": "Found Paper",
            "abstract": "Abstract text",
            "authors": [{"name": "Author"}],
            "citationCount": 10,
            "venue": "Venue",
            "url": "https://example.com",
            "fieldsOfStudy": [],
        }
        with patch(
            "semantic_scholar_client.request_manager"
        ) as mock_rm, patch(
            "semantic_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_paper.return_value = None

            async def fake_request(request_func, **kwargs):
                return paper_data

            mock_rm.deduplicated_request = AsyncMock(
                side_effect=fake_request
            )

            paper = await client.get_paper_by_id("test-id")
            assert paper is not None
            assert paper.title == "Found Paper"

    @pytest.mark.asyncio
    async def test_get_paper_by_id_not_found(self, client):
        """get_paper_by_id returns None when request fails."""
        with patch(
            "semantic_scholar_client.request_manager"
        ) as mock_rm, patch(
            "semantic_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_paper.return_value = None
            mock_rm.deduplicated_request = AsyncMock(
                side_effect=Exception("Not found")
            )

            paper = await client.get_paper_by_id("nonexistent")
            assert paper is None

    @pytest.mark.asyncio
    async def test_get_citations_success(self, client):
        """get_citations returns citing papers."""
        citations_data = {
            "data": [
                {
                    "citingPaper": {
                        "paperId": "citing-1",
                        "title": "Citing Paper",
                        "authors": [{"name": "Citer"}],
                        "citationCount": 5,
                        "venue": "Venue",
                    }
                }
            ]
        }
        with patch(
            "semantic_scholar_client.request_manager"
        ) as mock_rm, patch(
            "semantic_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_citations.return_value = None

            async def fake_request(request_func, **kwargs):
                return citations_data

            mock_rm.deduplicated_request = AsyncMock(
                side_effect=fake_request
            )

            papers = await client.get_citations("target-paper")
            assert len(papers) == 1
            assert papers[0].title == "Citing Paper"

    @pytest.mark.asyncio
    async def test_get_citations_failure_returns_empty(self, client):
        """get_citations returns empty list on failure."""
        with patch(
            "semantic_scholar_client.request_manager"
        ) as mock_rm, patch(
            "semantic_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_citations.return_value = None
            mock_rm.deduplicated_request = AsyncMock(
                side_effect=Exception("Error")
            )

            papers = await client.get_citations("paper-id")
            assert papers == []

    @pytest.mark.asyncio
    async def test_get_references_success(self, client):
        """get_references returns referenced papers."""
        references_data = {
            "data": [
                {
                    "citedPaper": {
                        "paperId": "ref-1",
                        "title": "Referenced Paper",
                        "authors": [{"name": "Ref Author"}],
                        "citationCount": 100,
                    }
                }
            ]
        }
        with patch(
            "semantic_scholar_client.request_manager"
        ) as mock_rm, patch(
            "semantic_scholar_client.cache_manager"
        ) as mock_cm:
            async def fake_request(request_func, **kwargs):
                return references_data

            mock_rm.deduplicated_request = AsyncMock(
                side_effect=fake_request
            )

            papers = await client.get_references("source-paper")
            assert len(papers) == 1
            assert papers[0].title == "Referenced Paper"

    @pytest.mark.asyncio
    async def test_search_by_author(self, client):
        """search_by_author delegates to search with author: prefix."""
        with patch.object(
            client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = SearchResult(
                papers=[],
                total_count=0,
                query="author:Test Author",
                source="semantic_scholar",
            )
            await client.search_by_author("Test Author")

            mock_search.assert_called_once_with(
                "author:Test Author", max_results=10
            )
