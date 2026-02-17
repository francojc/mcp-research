"""Tests for cache manager functionality.

CacheManager uses synchronous sqlite3 — all methods are sync, no await.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta

from cache_manager import CacheManager
from models import Paper, Author, SearchResult


class TestCacheManager:
    """Test cases for CacheManager."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create a CacheManager backed by a temp database."""
        db_path = str(tmp_path / "test_cache.db")
        return CacheManager(db_path=db_path)

    @pytest.fixture
    def sample_paper(self):
        """Sample paper for caching tests."""
        return Paper(
            id="cache-test-paper",
            title="Cache Test Paper",
            authors=[
                Author(
                    name="Cache Author",
                    affiliation="Test University",
                )
            ],
            abstract="This paper is used for cache testing.",
            published_date=datetime(2023, 6, 15),
            url="https://example.com/cache-paper",
            doi="10.1234/cache.test",
            venue="Cache Conference",
            citation_count=25,
            source="test",
            source_id="cache-test-paper",
        )

    @pytest.fixture
    def sample_search_result(self, sample_paper):
        """Sample search result for caching tests."""
        return SearchResult(
            papers=[sample_paper],
            total_count=1,
            query="cache test",
            source="test",
        )

    # -- Initialisation --

    def test_cache_initialization(self, cache):
        """Database tables are created on init."""
        import sqlite3

        with sqlite3.connect(cache.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}

        assert "search_cache" in tables
        assert "paper_cache" in tables
        assert "citation_cache" in tables

    # -- Search cache --

    def test_search_cache_roundtrip(self, cache, sample_search_result):
        """Store and retrieve a search result."""
        query = "roundtrip-test"
        source = "test"

        # Initially empty
        assert (
            cache.get_cached_search_result(query, source) is None
        )

        # Cache it
        cache.cache_search_result(
            query, source, sample_search_result
        )

        # Retrieve it
        cached = cache.get_cached_search_result(query, source)
        assert cached is not None
        assert cached.query == sample_search_result.query
        assert len(cached.papers) == 1
        assert cached.papers[0].title == "Cache Test Paper"

    # -- Paper cache --

    def test_paper_cache_roundtrip(self, cache, sample_paper):
        """Store and retrieve a paper."""
        paper_id = "cache-paper-id"
        source = "test"

        assert cache.get_cached_paper(paper_id, source) is None

        cache.cache_paper(paper_id, source, sample_paper)

        cached = cache.get_cached_paper(paper_id, source)
        assert cached is not None
        assert cached.title == sample_paper.title
        assert cached.doi == sample_paper.doi
        assert len(cached.authors) == 1

    # -- Citation cache --

    def test_citations_cache_roundtrip(self, cache):
        """Store and retrieve citations."""
        paper_id = "cited-paper"
        source = "test"
        citations = [
            Paper(
                id="citing-1",
                title="First Citing Paper",
                authors=[Author(name="Author A")],
                source="test",
                source_id="citing-1",
            ),
            Paper(
                id="citing-2",
                title="Second Citing Paper",
                authors=[Author(name="Author B")],
                source="test",
                source_id="citing-2",
            ),
        ]

        assert cache.get_cached_citations(paper_id, source) is None

        cache.cache_citations(paper_id, source, citations)

        cached = cache.get_cached_citations(paper_id, source)
        assert cached is not None
        assert len(cached) == 2
        assert cached[0].title == "First Citing Paper"
        assert cached[1].title == "Second Citing Paper"

    # -- Expiration --

    def test_expired_search_result_is_pruned(
        self, cache, sample_search_result
    ):
        """Expired entries are not returned."""
        query = "expire-test"
        source = "test"

        # Cache with 0-hour TTL (immediately expired)
        cache.cache_search_result(
            query, source, sample_search_result, ttl_hours=0
        )

        # Force the expiry by manipulating the DB directly
        import sqlite3

        cache_key = cache._generate_cache_key(
            "search", source, query
        )
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        with sqlite3.connect(cache.db_path) as conn:
            conn.execute(
                "UPDATE search_cache SET expires_at = ? "
                "WHERE cache_key = ?",
                (past, cache_key),
            )

        assert cache.get_cached_search_result(query, source) is None

    # -- Clean expired --

    def test_clean_expired_entries(
        self, cache, sample_search_result, sample_paper
    ):
        """clean_expired_entries removes stale data."""
        cache.cache_search_result(
            "q1", "test", sample_search_result
        )
        cache.cache_paper("p1", "test", sample_paper)

        # Manually expire everything
        import sqlite3

        past = (datetime.now() - timedelta(hours=1)).isoformat()
        with sqlite3.connect(cache.db_path) as conn:
            conn.execute(
                "UPDATE search_cache SET expires_at = ?", (past,)
            )
            conn.execute(
                "UPDATE paper_cache SET expires_at = ?", (past,)
            )

        counts = cache.clean_expired_entries()
        assert counts["search_cache"] >= 1
        assert counts["paper_cache"] >= 1

    # -- Stats --

    def test_cache_stats(
        self, cache, sample_search_result, sample_paper
    ):
        """get_cache_stats returns per-table counts."""
        cache.cache_search_result(
            "q1", "test", sample_search_result
        )
        cache.cache_paper("p1", "test", sample_paper)

        stats = cache.get_cache_stats()
        assert stats["search_cache"]["total"] >= 1
        assert stats["paper_cache"]["total"] >= 1

    # -- Clear --

    def test_clear_all_cache(
        self, cache, sample_search_result, sample_paper
    ):
        """clear_all_cache empties every table."""
        cache.cache_search_result(
            "q1", "test", sample_search_result
        )
        cache.cache_paper("p1", "test", sample_paper)

        cache.clear_all_cache()

        assert (
            cache.get_cached_search_result("q1", "test") is None
        )
        assert cache.get_cached_paper("p1", "test") is None

    # -- Key generation --

    def test_cache_key_uniqueness(self, cache):
        """Different inputs produce different keys."""
        k1 = cache._generate_cache_key("search", "arxiv", "q1")
        k2 = cache._generate_cache_key("search", "s2", "q1")
        k3 = cache._generate_cache_key("search", "arxiv", "q2")
        assert len({k1, k2, k3}) == 3

    # -- JSON round-trip with complex data --

    def test_paper_json_roundtrip(self, cache):
        """Paper with special characters survives cache."""
        paper = Paper(
            id="complex-1",
            title="Complex Paper",
            authors=[
                Author(name="First", affiliation="Uni 1"),
                Author(name="Second", affiliation="Uni 2"),
            ],
            abstract="Special chars: àáâãäå",
            published_date=datetime(2023, 6, 15, 14, 30, 45),
            categories=["cs.LG", "cs.AI", "stat.ML"],
            citation_count=42,
            source="test",
            source_id="complex-1",
        )

        cache.cache_paper("complex-1", "test", paper)
        cached = cache.get_cached_paper("complex-1", "test")

        assert cached is not None
        assert cached.title == paper.title
        assert len(cached.authors) == 2
        assert cached.abstract == paper.abstract
        assert cached.categories == paper.categories

    # -- Large data --

    def test_large_search_result(self, cache):
        """Caching a large result set works."""
        papers = [
            Paper(
                id=f"large-{i}",
                title=f"Large Paper {i}",
                authors=[Author(name=f"Author {i}")],
                abstract=f"Abstract {i} " * 20,
                source="test",
                source_id=f"large-{i}",
            )
            for i in range(50)
        ]
        result = SearchResult(
            papers=papers,
            total_count=50,
            query="large test",
            source="test",
        )

        cache.cache_search_result("large", "test", result)
        cached = cache.get_cached_search_result("large", "test")

        assert cached is not None
        assert len(cached.papers) == 50
        assert cached.papers[0].title == "Large Paper 0"

    # -- Database recovery --

    def test_database_recovery_from_corruption(self, tmp_path):
        """CacheManager raises on corrupted DB file.

        sqlite3 cannot open a file filled with garbage — the
        current CacheManager does not handle this, so the expected
        behaviour is a DatabaseError.  A future improvement could
        catch this and recreate the file.
        """
        import sqlite3

        db_path = str(tmp_path / "recovery.db")

        cache1 = CacheManager(db_path=db_path)
        cache1.cache_paper(
            "p1",
            "test",
            Paper(
                id="p1",
                title="Before",
                authors=[],
                source="test",
                source_id="p1",
            ),
        )

        # Corrupt the file
        with open(db_path, "w") as f:
            f.write("corrupted data")

        # CacheManager does not handle corruption gracefully
        with pytest.raises(sqlite3.DatabaseError):
            CacheManager(db_path=db_path)
