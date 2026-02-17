"""Tests for Google Scholar scraping client."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime

from bs4 import BeautifulSoup

from google_scholar_client import GoogleScholarClient
from models import Paper, Author, SearchResult


class TestGoogleScholarClient:
    """Test cases for GoogleScholarClient."""

    @pytest.fixture
    def client(self):
        """Create GoogleScholarClient instance for testing."""
        return GoogleScholarClient()

    # -- Unit tests for sync helpers --

    def test_detect_captcha_positive(self, client):
        """CAPTCHA indicators are detected."""
        cases = [
            "Please verify you are not a robot",
            '<div class="g-recaptcha"></div>',
            "unusual traffic from your network",
            "automated requests detected",
        ]
        for html in cases:
            assert client._detect_captcha(html) is True, html

    def test_detect_captcha_negative(self, client):
        """Normal content is not flagged as CAPTCHA."""
        assert client._detect_captcha(
            "<html>Normal content with papers</html>"
        ) is False
        assert client._detect_captcha("") is False

    def test_detect_blocked(self, client):
        """Blocked status codes and indicators are detected."""
        assert client._detect_blocked("", 429) is True
        assert client._detect_blocked("", 503) is True
        assert (
            client._detect_blocked(
                "your computer or network may be sending "
                "automated queries",
                200,
            )
            is True
        )
        assert client._detect_blocked("normal page", 200) is False

    def test_parse_authors(self, client):
        """Author names are extracted from GS author text."""
        authors = client._parse_authors(
            "J Doe, J Smith"
        )
        assert len(authors) >= 2
        names = [a.name for a in authors]
        assert "J Doe" in names
        assert "J Smith" in names

    def test_parse_authors_empty(self, client):
        """Empty string yields no authors."""
        assert client._parse_authors("") == []

    def test_parse_year(self, client):
        """Year extraction from text."""
        dt = client._parse_year("Some text 2023 more text")
        assert dt is not None
        assert dt.year == 2023

    def test_parse_year_none(self, client):
        """No year in text returns None."""
        assert client._parse_year("no year here") is None
        assert client._parse_year("") is None
        assert client._parse_year(None) is None

    def test_parse_citation_count(self, client):
        """Citation count extraction from GS link text."""
        assert client._parse_citation_count("Cited by 42") == 42
        assert client._parse_citation_count("Cited by 1") == 1
        assert (
            client._parse_citation_count("Cited by 1234") == 1234
        )
        assert client._parse_citation_count("No citations") is None
        assert client._parse_citation_count("") is None

    def test_extract_paper_data_complete(
        self, client, mock_google_scholar_html
    ):
        """Complete GS result div is parsed to Paper."""
        soup = BeautifulSoup(mock_google_scholar_html, "html.parser")
        result_div = soup.find("div", class_="gs_r")

        paper = client._extract_paper_data(result_div)

        assert paper is not None
        assert paper.title == "Test Google Scholar Paper"
        assert paper.source == "google_scholar"
        assert paper.citation_count == 15
        assert paper.url == "https://example.com/paper.pdf"

    def test_extract_paper_data_minimal(self, client):
        """Minimal result div with just a title."""
        html = """
        <div class="gs_r gs_or gs_scl">
            <div class="gs_ri">
                <h3 class="gs_rt">
                    <a href="https://example.com">Minimal Paper</a>
                </h3>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        result_div = soup.find("div", class_="gs_r")

        paper = client._extract_paper_data(result_div)
        assert paper is not None
        assert paper.title == "Minimal Paper"
        assert paper.citation_count is None

    def test_extract_paper_data_no_title_returns_none(self, client):
        """Result div with no title returns None."""
        html = '<div class="gs_r gs_or gs_scl"><div class="gs_ri"></div></div>'
        soup = BeautifulSoup(html, "html.parser")
        result_div = soup.find("div", class_="gs_r")

        paper = client._extract_paper_data(result_div)
        assert paper is None

    def test_get_rotated_headers(self, client):
        """Headers include User-Agent and standard browser headers."""
        headers = client._get_rotated_headers()
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert any(
            ua in headers["User-Agent"]
            for ua in ["Chrome", "Firefox", "Safari"]
        )

    def test_user_agent_rotation(self, client):
        """Successive calls rotate the User-Agent."""
        client._request_count = 0
        h1 = client._get_rotated_headers()["User-Agent"]
        client._request_count = 1
        h2 = client._get_rotated_headers()["User-Agent"]
        # With 6 user agents, index 0 and 1 should differ
        assert h1 != h2

    def test_build_advanced_query(self, client):
        """build_advanced_query constructs combined query."""
        q = client.build_advanced_query(
            "deep learning",
            author="Hinton",
            title="neural",
        )
        assert "deep learning" in q
        assert 'author:"Hinton"' in q
        assert 'intitle:"neural"' in q

    # -- Async tests using mocked request_manager --

    @pytest.mark.asyncio
    async def test_search_success(
        self, client, mock_google_scholar_html
    ):
        """Successful search parses HTML and returns papers."""
        with patch(
            "google_scholar_client.request_manager"
        ) as mock_rm, patch(
            "google_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_search_result.return_value = None

            # Build the expected SearchResult by parsing the HTML
            soup = BeautifulSoup(
                mock_google_scholar_html, "html.parser"
            )
            divs = soup.find_all(
                "div", class_="gs_r gs_or gs_scl"
            )
            papers = []
            for div in divs:
                p = client._extract_paper_data(div)
                if p:
                    papers.append(p)

            expected = SearchResult(
                papers=papers,
                total_count=None,
                query="machine learning",
                source="google_scholar",
            )

            async def fake_request(request_func, **kwargs):
                return expected

            mock_rm.deduplicated_request = AsyncMock(
                side_effect=fake_request
            )

            result = await client.search(
                "machine learning", max_results=1
            )

            assert isinstance(result, SearchResult)
            assert result.source == "google_scholar"
            assert len(result.papers) >= 1
            assert result.papers[0].title == "Test Google Scholar Paper"

    @pytest.mark.asyncio
    async def test_search_captcha_returns_empty(self, client):
        """CAPTCHA detection returns empty results."""
        with patch(
            "google_scholar_client.request_manager"
        ) as mock_rm, patch(
            "google_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_search_result.return_value = None

            captcha_result = SearchResult(
                papers=[],
                total_count=0,
                query="test",
                source="google_scholar",
            )

            async def fake_request(request_func, **kwargs):
                return captcha_result

            mock_rm.deduplicated_request = AsyncMock(
                side_effect=fake_request
            )

            result = await client.search("test")
            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0

    @pytest.mark.asyncio
    async def test_search_by_author(self, client):
        """search_by_author delegates with author: prefix."""
        with patch.object(
            client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = SearchResult(
                papers=[],
                total_count=0,
                query='author:"Test Author"',
                source="google_scholar",
            )
            await client.search_by_author("Test Author")

            mock_search.assert_called_once_with(
                'author:"Test Author"', max_results=10
            )

    @pytest.mark.asyncio
    async def test_get_paper_by_id_returns_none(self, client):
        """GS does not support direct ID lookup."""
        with patch(
            "google_scholar_client.cache_manager"
        ) as mock_cm:
            mock_cm.get_cached_paper.return_value = None
            result = await client.get_paper_by_id("gs_12345")
            assert result is None
