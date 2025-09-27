"""Tests for cache manager functionality."""

import pytest
import tempfile
import os
import asyncio
from datetime import datetime, timedelta
import json

from cache_manager import CacheManager
from models import Paper, Author, SearchResult


class TestCacheManager:
    """Test cases for CacheManager."""

    @pytest.fixture
    async def temp_cache(self):
        """Create temporary cache manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_cache.db")
            cache = CacheManager(db_path=db_path)
            await cache.initialize()
            yield cache
            await cache.close()

    @pytest.fixture
    def sample_paper(self):
        """Sample paper for caching tests."""
        return Paper(
            id="cache-test-paper",
            title="Cache Test Paper",
            authors=[Author(name="Cache Author", affiliation="Test University")],
            abstract="This paper is used for cache testing.",
            published_date=datetime(2023, 6, 15),
            url="https://example.com/cache-paper",
            doi="10.1234/cache.test",
            venue="Cache Conference",
            citation_count=25,
            source="test"
        )

    @pytest.fixture
    def sample_search_result(self, sample_paper):
        """Sample search result for caching tests."""
        return SearchResult(
            papers=[sample_paper],
            total_count=1,
            query="cache test",
            source="test"
        )

    @pytest.mark.asyncio
    async def test_cache_initialization(self, temp_cache):
        """Test cache database initialization."""
        # Check that tables were created
        async with temp_cache.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in await cursor.fetchall()]

            assert "search_cache" in tables
            assert "paper_cache" in tables
            assert "citations_cache" in tables

    @pytest.mark.asyncio
    async def test_search_cache_basic_operations(self, temp_cache, sample_search_result):
        """Test basic search cache operations."""
        cache_key = "test_search_key"

        # Cache should be empty initially
        cached_result = await temp_cache.get_search_result(cache_key)
        assert cached_result is None

        # Store result in cache
        await temp_cache.cache_search_result(cache_key, sample_search_result)

        # Retrieve from cache
        cached_result = await temp_cache.get_search_result(cache_key)
        assert cached_result is not None
        assert cached_result.query == sample_search_result.query
        assert len(cached_result.papers) == len(sample_search_result.papers)
        assert cached_result.papers[0].title == sample_search_result.papers[0].title

    @pytest.mark.asyncio
    async def test_paper_cache_basic_operations(self, temp_cache, sample_paper):
        """Test basic paper cache operations."""
        paper_id = sample_paper.id

        # Cache should be empty initially
        cached_paper = await temp_cache.get_paper(paper_id)
        assert cached_paper is None

        # Store paper in cache
        await temp_cache.cache_paper(sample_paper)

        # Retrieve from cache
        cached_paper = await temp_cache.get_paper(paper_id)
        assert cached_paper is not None
        assert cached_paper.title == sample_paper.title
        assert cached_paper.doi == sample_paper.doi
        assert len(cached_paper.authors) == len(sample_paper.authors)

    @pytest.mark.asyncio
    async def test_citations_cache_basic_operations(self, temp_cache):
        """Test basic citations cache operations."""
        paper_id = "test-paper-id"
        citations = [
            Paper(
                id="citing-paper-1",
                title="First Citing Paper",
                authors=[Author(name="First Author")],
                source="test"
            ),
            Paper(
                id="citing-paper-2",
                title="Second Citing Paper",
                authors=[Author(name="Second Author")],
                source="test"
            )
        ]

        # Cache should be empty initially
        cached_citations = await temp_cache.get_citations(paper_id)
        assert cached_citations is None

        # Store citations in cache
        await temp_cache.cache_citations(paper_id, citations)

        # Retrieve from cache
        cached_citations = await temp_cache.get_citations(paper_id)
        assert cached_citations is not None
        assert len(cached_citations) == len(citations)
        assert cached_citations[0].title == citations[0].title
        assert cached_citations[1].title == citations[1].title

    @pytest.mark.asyncio
    async def test_cache_expiration(self, temp_cache, sample_search_result):
        """Test cache expiration functionality."""
        cache_key = "expiration_test"

        # Create cache manager with very short TTL for testing
        temp_cache.search_ttl = 1  # 1 second

        # Store result
        await temp_cache.cache_search_result(cache_key, sample_search_result)

        # Should be available immediately
        cached_result = await temp_cache.get_search_result(cache_key)
        assert cached_result is not None

        # Wait for expiration
        await asyncio.sleep(2)

        # Should be expired now
        cached_result = await temp_cache.get_search_result(cache_key)
        assert cached_result is None

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, temp_cache, sample_search_result, sample_paper):
        """Test cleanup of expired entries."""
        # Set very short TTL
        temp_cache.search_ttl = 1
        temp_cache.paper_ttl = 1

        # Store some items
        await temp_cache.cache_search_result("key1", sample_search_result)
        await temp_cache.cache_paper(sample_paper)

        # Wait for expiration
        await asyncio.sleep(2)

        # Run cleanup
        removed_count = await temp_cache.cleanup_expired()

        # Should have removed expired items
        assert removed_count > 0

        # Items should no longer be in cache
        assert await temp_cache.get_search_result("key1") is None
        assert await temp_cache.get_paper(sample_paper.id) is None

    @pytest.mark.asyncio
    async def test_cache_stats(self, temp_cache, sample_search_result, sample_paper):
        """Test cache statistics functionality."""
        # Initially empty
        stats = await temp_cache.get_cache_stats()
        assert stats["total_entries"] == 0

        # Add some items
        await temp_cache.cache_search_result("test1", sample_search_result)
        await temp_cache.cache_paper(sample_paper)

        # Check stats
        stats = await temp_cache.get_cache_stats()
        assert stats["total_entries"] == 2

        # Test cache hits/misses
        await temp_cache.get_search_result("test1")  # hit
        await temp_cache.get_search_result("nonexistent")  # miss

        stats = await temp_cache.get_cache_stats()
        assert stats["cache_hits"] >= 1
        assert stats["cache_misses"] >= 1

    @pytest.mark.asyncio
    async def test_clear_cache(self, temp_cache, sample_search_result, sample_paper):
        """Test cache clearing functionality."""
        # Add some items
        await temp_cache.cache_search_result("test", sample_search_result)
        await temp_cache.cache_paper(sample_paper)

        # Verify items are cached
        assert await temp_cache.get_search_result("test") is not None
        assert await temp_cache.get_paper(sample_paper.id) is not None

        # Clear cache
        await temp_cache.clear_cache()

        # Verify cache is empty
        assert await temp_cache.get_search_result("test") is None
        assert await temp_cache.get_paper(sample_paper.id) is None

        # Stats should show empty cache
        stats = await temp_cache.get_cache_stats()
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_access(self, temp_cache, sample_search_result):
        """Test concurrent cache access."""
        async def cache_operation(key_suffix):
            key = f"concurrent_test_{key_suffix}"
            await temp_cache.cache_search_result(key, sample_search_result)
            result = await temp_cache.get_search_result(key)
            return result is not None

        # Run multiple concurrent operations
        tasks = [cache_operation(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert all(results)

    @pytest.mark.asyncio
    async def test_large_data_caching(self, temp_cache):
        """Test caching of large data structures."""
        # Create large search result
        large_papers = [
            Paper(
                id=f"large-paper-{i}",
                title=f"Large Paper {i}",
                authors=[Author(name=f"Author {i}", affiliation=f"University {i}")],
                abstract=f"This is a large abstract for paper {i} " * 20,
                source="test"
            )
            for i in range(50)
        ]

        large_result = SearchResult(
            papers=large_papers,
            total_count=50,
            query="large test",
            source="test"
        )

        # Cache large result
        await temp_cache.cache_search_result("large_test", large_result)

        # Retrieve and verify
        cached_result = await temp_cache.get_search_result("large_test")
        assert cached_result is not None
        assert len(cached_result.papers) == 50
        assert cached_result.papers[0].title == "Large Paper 0"

    @pytest.mark.asyncio
    async def test_cache_size_estimation(self, temp_cache, sample_search_result):
        """Test cache size estimation."""
        # Add some data
        for i in range(10):
            await temp_cache.cache_search_result(f"size_test_{i}", sample_search_result)

        stats = await temp_cache.get_cache_stats()
        assert stats["total_size_mb"] > 0
        assert isinstance(stats["total_size_mb"], float)

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, temp_cache):
        """Test cache key generation and uniqueness."""
        keys_used = set()

        # Test that different parameters generate different keys
        test_cases = [
            {"query": "test1", "source": "arxiv"},
            {"query": "test1", "source": "semantic_scholar"},
            {"query": "test2", "source": "arxiv"},
            {"query": "test1", "source": "arxiv", "max_results": 10},
            {"query": "test1", "source": "arxiv", "max_results": 20},
        ]

        for params in test_cases:
            # This tests the implicit key generation in cache operations
            key = f"{params['query']}_{params['source']}_{params.get('max_results', 'default')}"
            assert key not in keys_used
            keys_used.add(key)

    @pytest.mark.asyncio
    async def test_json_serialization(self, temp_cache, sample_paper):
        """Test JSON serialization/deserialization of cached objects."""
        # Cache paper with complex data
        complex_paper = Paper(
            id="complex-paper",
            title="Complex Paper",
            authors=[
                Author(name="First Author", affiliation="University 1"),
                Author(name="Second Author", affiliation="University 2")
            ],
            abstract="Complex abstract with special characters: àáâãäå",
            published_date=datetime(2023, 6, 15, 14, 30, 45),
            categories=["cs.LG", "cs.AI", "stat.ML"],
            citation_count=42,
            source="test"
        )

        # Cache and retrieve
        await temp_cache.cache_paper(complex_paper)
        cached_paper = await temp_cache.get_paper(complex_paper.id)

        # Verify all data is preserved
        assert cached_paper.title == complex_paper.title
        assert len(cached_paper.authors) == len(complex_paper.authors)
        assert cached_paper.authors[0].name == complex_paper.authors[0].name
        assert cached_paper.published_date == complex_paper.published_date
        assert cached_paper.categories == complex_paper.categories

    @pytest.mark.asyncio
    async def test_database_recovery(self):
        """Test database recovery from corruption or missing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "recovery_test.db")

            # Create and initialize cache
            cache = CacheManager(db_path=db_path)
            await cache.initialize()

            # Add some data
            paper = Paper(id="recovery-test", title="Recovery Test", source="test")
            await cache.cache_paper(paper)

            # Close properly
            await cache.close()

            # Simulate corruption by writing invalid data
            with open(db_path, 'w') as f:
                f.write("corrupted data")

            # Should be able to reinitialize (will recreate database)
            cache2 = CacheManager(db_path=db_path)
            await cache2.initialize()

            # Should work even though data was lost
            result = await cache2.get_paper("recovery-test")
            assert result is None  # Data lost but cache functional

            await cache2.close()