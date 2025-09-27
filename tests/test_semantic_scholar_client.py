"""Tests for Semantic Scholar API client."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime
import json

from semantic_scholar_client import SemanticScholarClient
from models import Paper, SearchResult


class TestSemanticScholarClient:
    """Test cases for SemanticScholarClient."""

    @pytest.fixture
    def client(self):
        """Create SemanticScholarClient instance for testing."""
        return SemanticScholarClient(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_search_success(self, client, mock_semantic_scholar_response):
        """Test successful search operation."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_semantic_scholar_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.search("machine learning", max_results=1)

            assert isinstance(result, SearchResult)
            assert result.source == "semantic_scholar"
            assert result.query == "machine learning"
            assert len(result.papers) == 1

            paper = result.papers[0]
            assert paper.title == "Test Semantic Scholar Paper"
            assert paper.abstract == "This is a test abstract from Semantic Scholar."
            assert paper.doi == "10.1234/test-semantic"
            assert paper.citation_count == 25
            assert paper.source == "semantic_scholar"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, client):
        """Test search with no results."""
        empty_response = {
            "total": 0,
            "offset": 0,
            "data": []
        }

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = empty_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.search("nonexistent topic")

            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_search_with_api_key(self, client):
        """Test search includes API key in headers."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"total": 0, "data": []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            await client.search("test")

            call_args = mock_get.call_args
            headers = call_args[1]["headers"]
            assert "X-API-KEY" in headers
            assert headers["X-API-KEY"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_search_rate_limit_error(self, client):
        """Test handling of rate limit errors."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_response.raise_for_status.side_effect = Exception("Rate limited")
            mock_get.return_value = mock_response

            result = await client.search("test query")

            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0

    @pytest.mark.asyncio
    async def test_get_paper_details_success(self, client):
        """Test successful paper details retrieval."""
        paper_data = {
            "paperId": "test-paper-id",
            "title": "Test Paper Details",
            "abstract": "Detailed abstract",
            "venue": "Test Venue",
            "year": 2023,
            "authors": [{"name": "Test Author", "authorId": "author-123"}],
            "citationCount": 50,
            "doi": "10.1234/detailed-paper",
            "url": "https://semanticscholar.org/paper/test",
            "fieldsOfStudy": ["Computer Science"]
        }

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = paper_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            paper = await client.get_paper_details("test-paper-id")

            assert isinstance(paper, Paper)
            assert paper.title == "Test Paper Details"
            assert paper.citation_count == 50
            assert paper.doi == "10.1234/detailed-paper"

    @pytest.mark.asyncio
    async def test_get_paper_details_not_found(self, client):
        """Test paper details retrieval for non-existent paper."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = Exception("Not found")
            mock_get.return_value = mock_response

            paper = await client.get_paper_details("nonexistent-id")

            assert paper is None

    @pytest.mark.asyncio
    async def test_get_citations_success(self, client):
        """Test successful citation retrieval."""
        citations_response = {
            "data": [
                {
                    "citingPaper": {
                        "paperId": "citing-paper-1",
                        "title": "Paper That Cites",
                        "abstract": "This paper cites the target paper",
                        "year": 2024,
                        "authors": [{"name": "Citing Author"}],
                        "citationCount": 5,
                        "venue": "Citation Conference"
                    }
                }
            ]
        }

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = citations_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            citations = await client.get_citations("target-paper-id")

            assert len(citations) == 1
            assert citations[0].title == "Paper That Cites"

    @pytest.mark.asyncio
    async def test_get_references_success(self, client):
        """Test successful reference retrieval."""
        references_response = {
            "data": [
                {
                    "citedPaper": {
                        "paperId": "referenced-paper-1",
                        "title": "Referenced Paper",
                        "abstract": "This paper is referenced",
                        "year": 2022,
                        "authors": [{"name": "Referenced Author"}],
                        "citationCount": 100,
                        "venue": "Reference Journal"
                    }
                }
            ]
        }

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = references_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            references = await client.get_references("source-paper-id")

            assert len(references) == 1
            assert references[0].title == "Referenced Paper"

    @pytest.mark.asyncio
    async def test_search_by_author(self, client):
        """Test search by author functionality."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"total": 0, "data": []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            await client.search_by_author("Test Author")

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert "author:" in params["query"] or "Test Author" in params["query"]

    def test_parse_paper_complete_data(self, client):
        """Test parsing paper with complete data."""
        paper_data = {
            "paperId": "complete-paper-id",
            "title": "Complete Test Paper",
            "abstract": "This is a complete paper with all fields",
            "venue": "Complete Conference",
            "year": 2023,
            "publicationDate": "2023-06-15",
            "authors": [
                {
                    "name": "Complete Author",
                    "authorId": "author-complete",
                    "affiliations": ["Complete University"]
                }
            ],
            "citationCount": 75,
            "doi": "10.1234/complete",
            "url": "https://semanticscholar.org/paper/complete",
            "fieldsOfStudy": ["Computer Science", "Machine Learning"],
            "s2FieldsOfStudy": [
                {"category": "Computer Science"},
                {"category": "Machine Learning"}
            ]
        }

        paper = client._parse_paper(paper_data)

        assert paper.id == "complete-paper-id"
        assert paper.title == "Complete Test Paper"
        assert paper.abstract == "This is a complete paper with all fields"
        assert paper.venue == "Complete Conference"
        assert paper.citation_count == 75
        assert paper.doi == "10.1234/complete"
        assert len(paper.authors) == 1
        assert paper.authors[0].name == "Complete Author"
        assert paper.authors[0].affiliation == "Complete University"
        assert "Computer Science" in paper.categories

    def test_parse_paper_minimal_data(self, client):
        """Test parsing paper with minimal required data."""
        paper_data = {
            "paperId": "minimal-paper-id",
            "title": "Minimal Paper"
        }

        paper = client._parse_paper(paper_data)

        assert paper.id == "minimal-paper-id"
        assert paper.title == "Minimal Paper"
        assert paper.abstract is None
        assert paper.venue is None
        assert paper.citation_count is None
        assert len(paper.authors) == 0

    def test_parse_paper_missing_id(self, client):
        """Test parsing paper without ID returns None."""
        paper_data = {
            "title": "No ID Paper"
        }

        paper = client._parse_paper(paper_data)
        assert paper is None

    @pytest.mark.asyncio
    async def test_search_with_year_filter(self, client):
        """Test search with year filtering."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"total": 0, "data": []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            await client.search("test", year=2023)

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert "year" in params

    @pytest.mark.asyncio
    async def test_search_with_fields_filter(self, client):
        """Test search with fields of study filtering."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"total": 0, "data": []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            await client.search("test", fields_of_study=["Computer Science"])

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert "fieldsOfStudy" in params

    @pytest.mark.asyncio
    async def test_client_without_api_key(self):
        """Test client functionality without API key."""
        client = SemanticScholarClient()

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"total": 0, "data": []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            await client.search("test")

            call_args = mock_get.call_args
            headers = call_args[1].get("headers", {})
            assert "X-API-KEY" not in headers

    @pytest.mark.asyncio
    async def test_json_decode_error(self, client):
        """Test handling of JSON decode errors."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.text = "Invalid JSON response"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.search("test")

            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0

    def test_build_search_url(self, client):
        """Test search URL building."""
        url = client._build_search_url()
        assert "graph/v1/paper/search" in url
        assert client.BASE_URL in url

    def test_build_paper_url(self, client):
        """Test paper URL building."""
        url = client._build_paper_url("test-paper-id")
        assert "test-paper-id" in url
        assert "graph/v1/paper" in url