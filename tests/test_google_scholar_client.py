"""Tests for Google Scholar scraping client."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime

from google_scholar_client import GoogleScholarClient
from models import Paper, SearchResult


class TestGoogleScholarClient:
    """Test cases for GoogleScholarClient."""

    @pytest.fixture
    def client(self):
        """Create GoogleScholarClient instance for testing."""
        return GoogleScholarClient()

    @pytest.mark.asyncio
    async def test_search_success(self, client, mock_google_scholar_html):
        """Test successful search operation."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_google_scholar_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.search("machine learning", max_results=1)

            assert isinstance(result, SearchResult)
            assert result.source == "google_scholar"
            assert result.query == "machine learning"
            assert len(result.papers) == 1

            paper = result.papers[0]
            assert paper.title == "Test Google Scholar Paper"
            assert "test abstract from Google Scholar" in paper.abstract
            assert paper.citation_count == 15
            assert paper.source == "google_scholar"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, client):
        """Test search with no results."""
        empty_html = """
        <html>
        <body>
            <div id="gs_res_ccl_mid">
                <div class="gs_r gs_or gs_scl" style="display:none">
                    <!-- No visible results -->
                </div>
            </div>
        </body>
        </html>
        """

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = empty_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.search("nonexistent topic")

            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0

    @pytest.mark.asyncio
    async def test_captcha_detection(self, client):
        """Test CAPTCHA detection and handling."""
        captcha_html = """
        <html>
        <body>
            <div>Please verify you are not a robot</div>
            <div class="g-recaptcha"></div>
        </body>
        </html>
        """

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = captcha_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.search("test query")

            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0
            # Should detect CAPTCHA and return empty results

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test rate limiting behavior."""
        with patch('httpx.AsyncClient.get') as mock_get, \
             patch('asyncio.sleep') as mock_sleep:

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<html><body></body></html>"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Make multiple requests
            await client.search("test1")
            await client.search("test2")

            # Should have introduced delays
            assert mock_sleep.call_count >= 1

    @pytest.mark.asyncio
    async def test_http_error_handling(self, client):
        """Test HTTP error handling."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.raise_for_status.side_effect = Exception("Service unavailable")
            mock_get.return_value = mock_response

            result = await client.search("test query")

            assert isinstance(result, SearchResult)
            assert len(result.papers) == 0

    def test_parse_paper_result_complete(self, client):
        """Test parsing paper result with complete data."""
        from bs4 import BeautifulSoup

        html = """
        <div class="gs_r gs_or gs_scl" data-lid="123">
            <div class="gs_ri">
                <h3 class="gs_rt">
                    <a href="https://example.com/paper.pdf">Complete Test Paper</a>
                </h3>
                <div class="gs_a">
                    John Doe, Jane Smith - Test Conference, 2023 - publisher.com
                </div>
                <div class="gs_rs">
                    This is a complete abstract with detailed information about the research.
                </div>
                <div class="gs_fl">
                    <a href="/scholar?cites=123456">Cited by 42</a>
                    <a href="/scholar?cluster=789">All 5 versions</a>
                </div>
            </div>
        </div>
        """

        soup = BeautifulSoup(html, 'html.parser')
        result_div = soup.find('div', class_='gs_r')

        paper = client._parse_paper_result(result_div)

        assert paper is not None
        assert paper.title == "Complete Test Paper"
        assert "complete abstract" in paper.abstract
        assert paper.url == "https://example.com/paper.pdf"
        assert paper.venue == "Test Conference"
        assert paper.citation_count == 42
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "John Doe"
        assert paper.authors[1].name == "Jane Smith"

    def test_parse_paper_result_minimal(self, client):
        """Test parsing paper result with minimal data."""
        from bs4 import BeautifulSoup

        html = """
        <div class="gs_r gs_or gs_scl">
            <div class="gs_ri">
                <h3 class="gs_rt">
                    <span>Minimal Paper Title</span>
                </h3>
            </div>
        </div>
        """

        soup = BeautifulSoup(html, 'html.parser')
        result_div = soup.find('div', class_='gs_r')

        paper = client._parse_paper_result(result_div)

        assert paper is not None
        assert paper.title == "Minimal Paper Title"
        assert paper.abstract == ""
        assert paper.url is None
        assert paper.citation_count is None

    def test_extract_authors_various_formats(self, client):
        """Test author extraction from various formats."""
        test_cases = [
            ("J Doe, J Smith - Conference, 2023", ["J Doe", "J Smith"]),
            ("Single Author - Journal 2022", ["Single Author"]),
            ("A, B, C - Venue", ["A", "B", "C"]),
            ("Author1, Author2, Author3, Author4 - Very Long Venue Name, 2021",
             ["Author1", "Author2", "Author3", "Author4"]),
            ("", []),
            ("No Authors Here - Just Venue, 2023", [])
        ]

        for author_text, expected in test_cases:
            authors = client._extract_authors(author_text)
            if expected:
                assert len(authors) == len(expected)
                for i, expected_name in enumerate(expected):
                    assert authors[i].name == expected_name
            else:
                assert len(authors) == 0

    def test_extract_citation_count(self, client):
        """Test citation count extraction."""
        test_cases = [
            ("Cited by 42", 42),
            ("Cited by 1", 1),
            ("Cited by 1234", 1234),
            ("No citations", None),
            ("", None),
            ("Cited by invalid", None)
        ]

        for text, expected in test_cases:
            result = client._extract_citation_count(text)
            assert result == expected

    def test_extract_venue_and_year(self, client):
        """Test venue and year extraction."""
        test_cases = [
            ("J Doe - Test Conference, 2023 - publisher", ("Test Conference", 2023)),
            ("Author - Journal of Science, 2022", ("Journal of Science", 2022)),
            ("A, B - Very Long Conference Name, 2021 - ieee.org",
             ("Very Long Conference Name", 2021)),
            ("No venue info", (None, None)),
            ("Author - Conference without year", (None, None)),
            ("Author - 2023", (None, 2023))  # Year only
        ]

        for text, expected in test_cases:
            venue, year = client._extract_venue_and_year(text)
            assert venue == expected[0]
            assert year == expected[1]

    def test_clean_title(self, client):
        """Test title cleaning functionality."""
        test_cases = [
            ("[PDF] Title with prefix", "Title with prefix"),
            ("[HTML] Another title", "Another title"),
            ("[CITATION] Citation title", "Citation title"),
            ("Normal title", "Normal title"),
            ("[PDF][HTML] Multiple prefixes", "Multiple prefixes"),
            ("", "")
        ]

        for input_title, expected in test_cases:
            result = client._clean_title(input_title)
            assert result == expected

    def test_detect_captcha(self, client):
        """Test CAPTCHA detection in various HTML content."""
        captcha_cases = [
            ("<html>Please verify you are not a robot</html>", True),
            ("<html><div class='g-recaptcha'></div></html>", True),
            ("<html>unusual traffic from your network</html>", True),
            ("<html>automated requests</html>", True),
            ("<html>Normal content with papers</html>", False),
            ("", False)
        ]

        for html_content, expected in captcha_cases:
            result = client._detect_captcha(html_content)
            assert result == expected

    def test_build_search_url(self, client):
        """Test search URL construction."""
        test_cases = [
            ("simple query", None, None),
            ("machine learning", 2020, 2023),
            ("complex query with spaces", 2022, None),
        ]

        for query, year_low, year_high in test_cases:
            url = client._build_search_url(query, year_low, year_high)

            assert "scholar.google.com" in url
            assert "q=" in url
            assert query.replace(" ", "+") in url or query in url

            if year_low:
                assert f"as_ylo={year_low}" in url
            if year_high:
                assert f"as_yhi={year_high}" in url

    @pytest.mark.asyncio
    async def test_search_with_year_range(self, client):
        """Test search with year range filtering."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<html><body></body></html>"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            await client.search("test", year_low=2020, year_high=2023)

            call_args = mock_get.call_args
            url = call_args[0][0]
            assert "as_ylo=2020" in url
            assert "as_yhi=2023" in url

    @pytest.mark.asyncio
    async def test_user_agent_rotation(self, client):
        """Test user agent rotation in requests."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<html><body></body></html>"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            await client.search("test")

            call_args = mock_get.call_args
            headers = call_args[1]["headers"]
            assert "User-Agent" in headers
            # Should be one of the predefined user agents
            assert any(ua in headers["User-Agent"] for ua in ["Chrome", "Firefox", "Safari"])

    @pytest.mark.asyncio
    async def test_request_headers(self, client):
        """Test that proper headers are included in requests."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<html><body></body></html>"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            await client.search("test")

            call_args = mock_get.call_args
            headers = call_args[1]["headers"]

            # Check for essential headers
            assert "User-Agent" in headers
            assert "Accept" in headers
            assert "Accept-Language" in headers
            assert "Accept-Encoding" in headers