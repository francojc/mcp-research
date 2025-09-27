"""Test configuration and fixtures for MCP Research Server tests."""

import pytest
import asyncio
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator

from models import Paper, Author, SearchResult
from cache_manager import CacheManager
from request_manager import RequestManager


@pytest.fixture
def sample_paper():
    """Sample paper for testing."""
    return Paper(
        id="test-paper-1",
        title="Test Paper on Machine Learning",
        authors=[
            Author(name="John Doe", affiliation="Test University"),
            Author(name="Jane Smith", affiliation="Example Corp")
        ],
        abstract="This is a test paper about machine learning algorithms and their applications.",
        published_date=datetime(2023, 6, 15),
        url="https://arxiv.org/abs/test.1234",
        doi="10.1234/test.paper",
        arxiv_id="test.1234",
        venue="Test Conference on AI",
        categories=["cs.LG", "cs.AI"],
        citation_count=42,
        source="arxiv"
    )


@pytest.fixture
def sample_papers(sample_paper):
    """Multiple sample papers for testing."""
    papers = [sample_paper]

    # Create variations
    for i in range(2, 6):
        paper = Paper(
            id=f"test-paper-{i}",
            title=f"Test Paper {i} on Deep Learning",
            authors=[Author(name=f"Author {i}", affiliation=f"University {i}")],
            abstract=f"This is test paper {i} about deep learning and neural networks.",
            published_date=datetime(2023, 6, 15) - timedelta(days=i*30),
            url=f"https://arxiv.org/abs/test.{i}234",
            doi=f"10.1234/test.paper.{i}",
            arxiv_id=f"test.{i}234",
            venue=f"Test Conference {i}",
            categories=["cs.LG", "cs.AI"],
            citation_count=10 * i,
            source="arxiv"
        )
        papers.append(paper)

    return papers


@pytest.fixture
def sample_search_result(sample_papers):
    """Sample search result for testing."""
    return SearchResult(
        papers=sample_papers[:3],
        total_count=3,
        query="machine learning",
        source="arxiv"
    )


@pytest.fixture
async def temp_cache_manager():
    """Temporary cache manager for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_cache.db")
        cache_manager = CacheManager(db_path=db_path)
        await cache_manager.initialize()
        yield cache_manager
        await cache_manager.close()


@pytest.fixture
def request_manager():
    """Request manager instance for testing."""
    return RequestManager()


@pytest.fixture
def mock_http_response():
    """Mock HTTP response data."""
    return {
        "status_code": 200,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"results": []},
        "text": '{"results": []}'
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_arxiv_response():
    """Mock arXiv API response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query</title>
  <id>http://arxiv.org/api/query</id>
  <updated>2023-06-15T00:00:00-04:00</updated>
  <opensearch:totalResults>1</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>1</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/2306.12345v1</id>
    <updated>2023-06-15T17:59:59Z</updated>
    <published>2023-06-15T17:59:59Z</published>
    <title>Test Machine Learning Paper</title>
    <summary>This is a test abstract about machine learning.</summary>
    <author>
      <name>Test Author</name>
    </author>
    <arxiv:doi>10.1234/test</arxiv:doi>
    <link title="pdf" href="http://arxiv.org/pdf/2306.12345v1" rel="related" type="application/pdf"/>
    <arxiv:primary_category term="cs.LG"/>
    <category term="cs.LG"/>
    <category term="stat.ML"/>
  </entry>
</feed>"""


@pytest.fixture
def mock_semantic_scholar_response():
    """Mock Semantic Scholar API response."""
    return {
        "total": 1,
        "offset": 0,
        "data": [
            {
                "paperId": "test-semantic-scholar-id",
                "title": "Test Semantic Scholar Paper",
                "abstract": "This is a test abstract from Semantic Scholar.",
                "venue": "Test Venue",
                "year": 2023,
                "authors": [
                    {
                        "name": "Test Author",
                        "authorId": "test-author-id"
                    }
                ],
                "citationCount": 25,
                "doi": "10.1234/test-semantic",
                "url": "https://www.semanticscholar.org/paper/test",
                "fieldsOfStudy": ["Computer Science", "Machine Learning"]
            }
        ]
    }


@pytest.fixture
def mock_google_scholar_html():
    """Mock Google Scholar HTML response."""
    return """
    <html>
    <body>
        <div class="gs_r gs_or gs_scl" data-lid="123">
            <div class="gs_ri">
                <h3 class="gs_rt">
                    <a href="https://example.com/paper.pdf">Test Google Scholar Paper</a>
                </h3>
                <div class="gs_a">
                    Test Author - Test Venue, 2023
                </div>
                <div class="gs_rs">
                    This is a test abstract from Google Scholar search results.
                </div>
                <div class="gs_fl">
                    <a href="/scholar?cites=123456">Cited by 15</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """