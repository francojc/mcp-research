"""Tests for ArXiv API client."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime

from arxiv_client import ArxivClient
from models import Paper, SearchResult


class TestArxivClient:
    """Test cases for ArxivClient."""

    @pytest.fixture
    def client(self):
        """Create ArxivClient instance for testing."""
        return ArxivClient()

    @pytest.mark.asyncio
    async def test_search_success(self, client, mock_arxiv_response):
        """Test successful search operation."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_arxiv_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.search("machine learning", max_results=1)

            assert isinstance(result, SearchResult)
            assert result.source == "arxiv"
            assert result.query == "machine learning"
            assert len(result.papers) == 1

            paper = result.papers[0]
            assert paper.title == "Test Machine Learning Paper"
            assert paper.abstract == "This is a test abstract about machine learning."
            assert paper.arxiv_id == "2306.12345v1"
            assert paper.doi == "10.1234/test"
            assert paper.source == "arxiv"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, client):
        """Test search with no results."""
        empty_response = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query</title>
  <opensearch:totalResults>0</opensearch:totalResults>
</feed>"""

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = empty_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.search("nonexistent topic")

            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_search_http_error(self, client):
        """Test search with HTTP error."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = Exception("HTTP 500")
            mock_get.return_value = mock_response

            result = await client.search("test query")

            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_get_paper_details_success(self, client, mock_arxiv_response):
        """Test successful paper details retrieval."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_arxiv_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            paper = await client.get_paper_details("2306.12345")

            assert isinstance(paper, Paper)
            assert paper.title == "Test Machine Learning Paper"
            assert paper.arxiv_id == "2306.12345v1"
            assert paper.doi == "10.1234/test"

    @pytest.mark.asyncio
    async def test_get_paper_details_not_found(self, client):
        """Test paper details retrieval for non-existent paper."""
        empty_response = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <opensearch:totalResults>0</opensearch:totalResults>
</feed>"""

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = empty_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            paper = await client.get_paper_details("nonexistent.123")

            assert paper is None

    def test_parse_entry_complete_data(self, client):
        """Test parsing entry with complete data."""
        from xml.etree.ElementTree import fromstring

        entry_xml = """
        <entry xmlns:arxiv="http://arxiv.org/schemas/atom">
            <id>http://arxiv.org/abs/2306.12345v1</id>
            <title>Test Paper Title</title>
            <summary>Test abstract content</summary>
            <published>2023-06-15T17:59:59Z</published>
            <updated>2023-06-15T17:59:59Z</updated>
            <author><name>John Doe</name><arxiv:affiliation>Test University</arxiv:affiliation></author>
            <author><name>Jane Smith</name></author>
            <arxiv:doi>10.1234/test</arxiv:doi>
            <link href="http://arxiv.org/abs/2306.12345v1" rel="alternate" type="text/html"/>
            <arxiv:primary_category term="cs.LG"/>
            <category term="cs.LG"/>
            <category term="stat.ML"/>
        </entry>
        """

        entry = fromstring(entry_xml)
        paper = client._parse_entry(entry)

        assert paper.title == "Test Paper Title"
        assert paper.abstract == "Test abstract content"
        assert paper.arxiv_id == "2306.12345v1"
        assert paper.doi == "10.1234/test"
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "John Doe"
        assert paper.authors[0].affiliation == "Test University"
        assert paper.authors[1].name == "Jane Smith"
        assert paper.authors[1].affiliation is None
        assert "cs.LG" in paper.categories
        assert "stat.ML" in paper.categories

    def test_parse_entry_minimal_data(self, client):
        """Test parsing entry with minimal required data."""
        from xml.etree.ElementTree import fromstring

        entry_xml = """
        <entry>
            <id>http://arxiv.org/abs/1234.5678</id>
            <title>Minimal Paper</title>
            <summary>Minimal abstract</summary>
            <published>2023-01-01T00:00:00Z</published>
        </entry>
        """

        entry = fromstring(entry_xml)
        paper = client._parse_entry(entry)

        assert paper.title == "Minimal Paper"
        assert paper.abstract == "Minimal abstract"
        assert paper.arxiv_id == "1234.5678"
        assert paper.doi is None
        assert len(paper.authors) == 0
        assert len(paper.categories) == 0

    def test_extract_arxiv_id(self, client):
        """Test arXiv ID extraction from various formats."""
        test_cases = [
            ("http://arxiv.org/abs/2306.12345v1", "2306.12345v1"),
            ("http://arxiv.org/abs/2306.12345", "2306.12345"),
            ("https://arxiv.org/abs/1234.5678v2", "1234.5678v2"),
            ("arxiv:2306.12345", "2306.12345"),
            ("2306.12345v1", "2306.12345v1"),
            ("invalid-id", "invalid-id"),  # Should return as-is if no match
        ]

        for input_id, expected in test_cases:
            result = client._extract_arxiv_id(input_id)
            assert result == expected

    @pytest.mark.asyncio
    async def test_search_by_author(self, client, mock_arxiv_response):
        """Test search by author functionality."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_arxiv_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.search_by_author("Test Author")

            assert isinstance(result, SearchResult)
            mock_get.assert_called_once()

            # Check that the query includes author search
            call_args = mock_get.call_args
            assert "au:" in call_args[1]["params"]["search_query"]

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test that rate limiting is respected."""
        with patch('httpx.AsyncClient.get') as mock_get, \
             patch('asyncio.sleep') as mock_sleep:

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = """<?xml version="1.0"?><feed><opensearch:totalResults>0</opensearch:totalResults></feed>"""
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Make multiple requests quickly
            await client.search("test1")
            await client.search("test2")

            # Should have introduced delays for rate limiting
            assert mock_sleep.call_count >= 1

    def test_build_query_string(self, client):
        """Test query string building."""
        test_cases = [
            ("simple query", "simple query"),
            ("query with spaces", "query with spaces"),
            ("query+with+plus", "query+with+plus"),
        ]

        for input_query, expected in test_cases:
            result = client._build_query_string(input_query)
            assert expected in result

    @pytest.mark.asyncio
    async def test_search_with_date_filter(self, client):
        """Test search with date filtering."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = """<?xml version="1.0"?><feed><opensearch:totalResults>0</opensearch:totalResults></feed>"""
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            from datetime import date
            start_date = date(2023, 1, 1)
            end_date = date(2023, 12, 31)

            await client.search("test", start_date=start_date, end_date=end_date)

            call_args = mock_get.call_args
            params = call_args[1]["params"]

            # arXiv doesn't have native date filtering, so dates should be in query
            assert "2023" in params["search_query"] or "submittedDate" in params