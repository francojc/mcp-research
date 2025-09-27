"""Google Scholar scraper with robust anti-bot measures and error handling."""

import asyncio
import logging
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import quote, urlencode

import httpx
from bs4 import BeautifulSoup

from models import Author, Paper, SearchResult
from cache_manager import cache_manager
from request_manager import request_manager, RetryConfig

logger = logging.getLogger(__name__)


class GoogleScholarClient:
    """Robust Google Scholar scraper with anti-bot measures."""

    BASE_URL = "https://scholar.google.com"
    SEARCH_URL = f"{BASE_URL}/scholar"

    def __init__(self, delay_range: tuple = (10, 30), max_results_per_request: int = 10):
        self.delay_range = delay_range
        self.max_results_per_request = max_results_per_request
        self._session_initialized = False
        self._request_count = 0

        # Multiple realistic user agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]

        # Base headers (User-Agent will be rotated)
        self.base_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-User': '?1'
        }

        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _get_rotated_headers(self) -> Dict[str, str]:
        """Get headers with rotated user agent."""
        headers = self.base_headers.copy()
        # Rotate user agent based on request count
        ua_index = self._request_count % len(self.user_agents)
        headers['User-Agent'] = self.user_agents[ua_index]

        # Add referer for requests after the first one
        if self._session_initialized:
            headers['Referer'] = 'https://scholar.google.com/'

        return headers

    async def _calculate_enhanced_delay(self) -> float:
        """Calculate enhanced delay with longer pauses for human-like behavior."""
        # Base delay between requests
        base_delay = random.uniform(*self.delay_range)

        # Add longer pauses every 5-10 requests to simulate human behavior
        if self._request_count > 0 and self._request_count % random.randint(5, 10) == 0:
            extra_delay = random.uniform(60, 120)  # 1-2 minute pause
            logger.info(f"Adding extended pause of {extra_delay:.1f}s for human-like behavior")
            base_delay += extra_delay

        logger.debug(f"Request delay: {base_delay:.1f}s (request #{self._request_count})")
        return base_delay

    async def _warm_session(self):
        """Warm up the session by visiting the Scholar homepage."""
        if self._session_initialized:
            return

        logger.info("Warming up Google Scholar session...")

        try:
            # Visit the homepage first to establish session
            headers = self._get_rotated_headers()
            response = await self._client.get(self.BASE_URL, headers=headers)

            if response.status_code == 200:
                logger.info("Session warmed successfully")
                self._session_initialized = True

                # Small delay after warming
                await asyncio.sleep(random.uniform(2, 5))
            else:
                logger.warning(f"Session warming returned status {response.status_code}")

        except Exception as e:
            logger.warning(f"Session warming failed: {e}")
            # Continue anyway - don't fail the whole request

        # Always mark as initialized to avoid infinite retries
        self._session_initialized = True

    def _detect_captcha(self, html_content: str) -> bool:
        """Detect if Google Scholar is showing a CAPTCHA."""
        captcha_indicators = [
            'captcha',
            'unusual traffic',
            'automated requests',
            'verify you are not a robot',
            'recaptcha',
            'gs_captcha_ccl',
            'solve the captcha'
        ]

        html_lower = html_content.lower()
        return any(indicator in html_lower for indicator in captcha_indicators)

    def _detect_blocked(self, html_content: str, status_code: int) -> bool:
        """Detect if IP is blocked or rate limited."""
        if status_code in [429, 503]:
            return True

        blocked_indicators = [
            'your computer or network may be sending automated queries',
            'unusual traffic from your computer network',
            'please make sure your browser supports javascript',
            'blocked'
        ]

        html_lower = html_content.lower()
        return any(indicator in html_lower for indicator in blocked_indicators)

    def _parse_authors(self, author_text: str) -> List[Author]:
        """Parse author information from Google Scholar."""
        if not author_text:
            return []

        authors = []
        # Handle various author formats
        author_parts = re.split(r',|\band\b', author_text)

        for author_part in author_parts:
            author_name = author_part.strip()
            if author_name and len(author_name) > 1:
                # Remove year patterns and other noise
                author_name = re.sub(r'\s*-?\s*\d{4}.*$', '', author_name)
                author_name = re.sub(r'^\W+|\W+$', '', author_name)

                if author_name and len(author_name) > 1:
                    authors.append(Author(name=author_name))

        return authors[:10]  # Limit to reasonable number

    def _parse_year(self, text: str) -> Optional[datetime]:
        """Extract publication year from text."""
        if not text:
            return None

        # Look for 4-digit year patterns
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        if year_match:
            try:
                year = int(year_match.group())
                if 1900 <= year <= datetime.now().year + 5:  # Reasonable year range
                    return datetime(year, 1, 1)
            except ValueError:
                pass

        return None

    def _parse_citation_count(self, cite_text: str) -> Optional[int]:
        """Extract citation count from citation link text."""
        if not cite_text:
            return None

        # Look for "Cited by X" pattern
        cite_match = re.search(r'cited by (\d+)', cite_text.lower())
        if cite_match:
            try:
                return int(cite_match.group(1))
            except ValueError:
                pass

        return None

    def _extract_paper_data(self, result_div) -> Optional[Paper]:
        """Extract paper data from a Google Scholar result div."""
        try:
            # Title and URL
            title_link = result_div.find('h3', class_='gs_rt')
            if not title_link:
                return None

            title_anchor = title_link.find('a')
            title = title_anchor.get_text(strip=True) if title_anchor else title_link.get_text(strip=True)
            url = title_anchor.get('href') if title_anchor else None

            if not title:
                return None

            # Clean title
            title = re.sub(r'^\[.*?\]\s*', '', title)  # Remove [PDF], [BOOK], etc.
            title = title.strip()

            # Authors and publication info
            authors_div = result_div.find('div', class_='gs_a')
            authors = []
            venue = None
            pub_year = None

            if authors_div:
                author_text = authors_div.get_text()

                # Split on " - " to separate authors, venue, and year
                parts = [p.strip() for p in author_text.split(' - ')]

                if parts:
                    # First part is usually authors
                    authors = self._parse_authors(parts[0])

                    # Look for venue in remaining parts
                    for part in parts[1:]:
                        if part and not re.match(r'^\d{4}$', part):
                            # This looks like a venue
                            venue = part
                            break

                    # Look for year in any part
                    for part in parts:
                        year_date = self._parse_year(part)
                        if year_date:
                            pub_year = year_date
                            break

            # Abstract/snippet
            snippet_div = result_div.find('div', class_='gs_rs')
            abstract = snippet_div.get_text(strip=True) if snippet_div else None

            # Citation count
            citation_count = None
            cite_links = result_div.find_all('a', string=lambda text: text and 'cited by' in text.lower())
            for cite_link in cite_links:
                citation_count = self._parse_citation_count(cite_link.get_text())
                if citation_count is not None:
                    break

            # Generate paper ID
            paper_id = f"gs_{abs(hash(title + str(authors[0].name if authors else 'unknown')))}"

            # Look for PDF links
            pdf_url = None
            pdf_links = result_div.find_all('a', string=lambda text: text and '[PDF]' in text)
            if pdf_links:
                pdf_url = pdf_links[0].get('href')

            return Paper(
                id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract,
                published_date=pub_year,
                url=url,
                pdf_url=pdf_url,
                venue=venue,
                citation_count=citation_count,
                source="google_scholar",
                source_id=paper_id,
                categories=[]
            )

        except Exception as e:
            logger.error(f"Failed to parse Google Scholar result: {e}")
            return None

    async def search(
        self,
        query: str,
        max_results: int = 10,
        start: int = 0,
        year_low: Optional[int] = None,
        year_high: Optional[int] = None
    ) -> SearchResult:
        """
        Search Google Scholar for papers.

        Args:
            query: Search query
            max_results: Maximum results to return
            start: Starting index
            year_low: Earliest publication year
            year_high: Latest publication year
        """
        # Check cache first
        cache_key_params = f"{query}|{max_results}|{start}|{year_low}|{year_high}"
        cached_result = cache_manager.get_cached_search_result(cache_key_params, "google_scholar")
        if cached_result:
            logger.debug(f"Returning cached Google Scholar search result for query: {query}")
            return cached_result

        # Build search parameters
        params = {
            'q': query,
            'num': min(max_results, self.max_results_per_request),
            'start': start,
            'as_sdt': '0,5',  # Include patents and citations
        }

        # Add date range if specified
        if year_low is not None and year_high is not None:
            params['as_ylo'] = str(year_low)
            params['as_yhi'] = str(year_high)
        elif year_low is not None:
            params['as_ylo'] = str(year_low)
        elif year_high is not None:
            params['as_yhi'] = str(year_high)

        async def _execute_search():
            # Warm session first
            await self._warm_session()

            # Enhanced delay with human-like behavior
            delay = await self._calculate_enhanced_delay()
            await asyncio.sleep(delay)

            # Get rotated headers for this request
            headers = self._get_rotated_headers()
            self._request_count += 1

            response = await self._client.get(self.SEARCH_URL, params=params, headers=headers)

            # Check for blocking/captcha before parsing
            html_content = response.text

            if self._detect_captcha(html_content):
                logger.warning("CAPTCHA detected - Google Scholar requires human verification")
                # Return empty result instead of crashing the entire search
                return SearchResult(
                    papers=[],
                    total_count=0,
                    query=query,
                    source="google_scholar",
                    next_token=None
                )

            if self._detect_blocked(html_content, response.status_code):
                logger.warning(f"Blocked by Google Scholar (status: {response.status_code})")
                # Return empty result instead of crashing the entire search
                return SearchResult(
                    papers=[],
                    total_count=0,
                    query=query,
                    source="google_scholar",
                    next_token=None
                )

            if response.status_code != 200:
                logger.warning(f"Google Scholar returned status {response.status_code}")
                # Return empty result instead of crashing
                return SearchResult(
                    papers=[],
                    total_count=0,
                    query=query,
                    source="google_scholar",
                    next_token=None
                )

            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find result divs
            result_divs = soup.find_all('div', class_='gs_r gs_or gs_scl')

            papers = []
            for result_div in result_divs:
                paper = self._extract_paper_data(result_div)
                if paper:
                    papers.append(paper)
                    # Cache individual papers
                    cache_manager.cache_paper(paper.source_id, "google_scholar", paper, ttl_hours=48)

            return SearchResult(
                papers=papers,
                total_count=None,  # Google Scholar doesn't provide total count
                query=query,
                source="google_scholar"
            )

        try:
            # Use request manager with conservative retry settings for Google Scholar
            retry_config = RetryConfig(
                max_retries=1,  # Very conservative - don't hammer Google
                base_delay=10.0,  # Long delays
                max_delay=60.0
            )

            result = await request_manager.deduplicated_request(
                _execute_search,
                endpoint="google_scholar_search",
                retry_config=retry_config,
                min_interval=8.0  # Minimum 8 seconds between requests
            )

            # Cache the result
            cache_manager.cache_search_result(cache_key_params, "google_scholar", result, ttl_hours=24)
            logger.debug(f"Cached Google Scholar search result for query: {query}")

            return result

        except Exception as e:
            logger.error(f"Google Scholar search failed: {e}")
            # Don't re-raise CAPTCHA/blocking errors - return empty results instead
            if "CAPTCHA" in str(e) or "Blocked" in str(e):
                logger.warning(f"Google Scholar access limited: {e}")
                return SearchResult(
                    papers=[],
                    total_count=0,
                    query=query,
                    source="google_scholar"
                )
            raise

    async def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """Get paper by ID (limited for Google Scholar)."""
        # Check cache first
        cached_paper = cache_manager.get_cached_paper(paper_id, "google_scholar")
        if cached_paper:
            logger.debug(f"Returning cached Google Scholar paper: {paper_id}")
            return cached_paper

        # For Google Scholar, we can't directly get papers by ID
        # This would require storing the original search query
        logger.warning("Direct paper retrieval by ID not supported for Google Scholar")
        return None

    async def search_by_author(self, author_name: str, max_results: int = 10) -> SearchResult:
        """Search for papers by author name."""
        query = f'author:"{author_name}"'
        return await self.search(query, max_results=max_results)

    def build_advanced_query(
        self,
        query: str,
        author: Optional[str] = None,
        title: Optional[str] = None,
        publication: Optional[str] = None,
        year_low: Optional[int] = None,
        year_high: Optional[int] = None,
        exact_phrase: Optional[str] = None,
        any_words: Optional[str] = None,
        without_words: Optional[str] = None
    ) -> str:
        """Build advanced Google Scholar search query."""
        query_parts = []

        # Base query
        if query:
            query_parts.append(query)

        # Author search
        if author:
            query_parts.append(f'author:"{author}"')

        # Title search
        if title:
            query_parts.append(f'intitle:"{title}"')

        # Publication search
        if publication:
            query_parts.append(f'source:"{publication}"')

        # Exact phrase
        if exact_phrase:
            query_parts.append(f'"{exact_phrase}"')

        # Any of these words
        if any_words:
            words = any_words.split()
            if len(words) > 1:
                query_parts.append(f"({' OR '.join(words)})")
            else:
                query_parts.append(any_words)

        # Without these words
        if without_words:
            words = without_words.split()
            for word in words:
                query_parts.append(f'-{word}')

        return ' '.join(query_parts)


# Global Google Scholar client instance
google_scholar_client = GoogleScholarClient()