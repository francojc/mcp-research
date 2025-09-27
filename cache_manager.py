"""SQLite-based caching system for academic paper data."""

import json
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from models import Paper, SearchResult

logger = logging.getLogger(__name__)


class CacheManager:
    """SQLite-based cache manager for API responses."""

    def __init__(self, db_path: str = "cache.db", default_ttl_hours: int = 24):
        self.db_path = Path(db_path)
        self.default_ttl_hours = default_ttl_hours
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    source TEXT NOT NULL,
                    result_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_cache (
                    cache_key TEXT PRIMARY KEY,
                    paper_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    paper_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS citation_cache (
                    cache_key TEXT PRIMARY KEY,
                    paper_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    citation_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP NOT NULL
                )
            """)

            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_search_cache_expires ON search_cache(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_paper_cache_expires ON paper_cache(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_citation_cache_expires ON citation_cache(expires_at)")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_search_cache_source_query ON search_cache(source, query)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_paper_cache_source_id ON paper_cache(source, paper_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_citation_cache_source_id ON citation_cache(source, paper_id)")

    def _generate_cache_key(self, *args) -> str:
        """Generate a consistent cache key from arguments."""
        key_string = "|".join(str(arg) for arg in args)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _is_expired(self, expires_at: str) -> bool:
        """Check if a cache entry has expired."""
        expire_time = datetime.fromisoformat(expires_at)
        return datetime.now() > expire_time

    def _update_hit_count(self, table: str, cache_key: str):
        """Update hit count and last accessed time for a cache entry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                UPDATE {table}
                SET hit_count = hit_count + 1, last_accessed = ?
                WHERE cache_key = ?
            """, (datetime.now().isoformat(), cache_key))

    def cache_search_result(
        self,
        query: str,
        source: str,
        result: SearchResult,
        ttl_hours: Optional[int] = None
    ) -> None:
        """Cache a search result."""
        cache_key = self._generate_cache_key("search", source, query)
        ttl = ttl_hours or self.default_ttl_hours
        expires_at = datetime.now() + timedelta(hours=ttl)

        # Convert SearchResult to dict for JSON serialization using Pydantic's serialization
        result_data = result.model_dump(mode='json')

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO search_cache
                (cache_key, query, source, result_data, created_at, expires_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                query,
                source,
                json.dumps(result_data),
                datetime.now().isoformat(),
                expires_at.isoformat(),
                datetime.now().isoformat()
            ))

        logger.debug(f"Cached search result for query='{query}', source='{source}'")

    def get_cached_search_result(self, query: str, source: str) -> Optional[SearchResult]:
        """Retrieve a cached search result."""
        cache_key = self._generate_cache_key("search", source, query)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT result_data, expires_at FROM search_cache
                WHERE cache_key = ?
            """, (cache_key,))

            row = cursor.fetchone()
            if not row:
                return None

            result_data, expires_at = row

            if self._is_expired(expires_at):
                # Clean up expired entry
                conn.execute("DELETE FROM search_cache WHERE cache_key = ?", (cache_key,))
                return None

            # Update hit count
            self._update_hit_count("search_cache", cache_key)

            # Reconstruct SearchResult
            data = json.loads(result_data)
            papers = [Paper(**paper_data) for paper_data in data["papers"]]

            logger.debug(f"Cache hit for search query='{query}', source='{source}'")
            return SearchResult(
                papers=papers,
                total_count=data["total_count"],
                query=data["query"],
                source=data["source"],
                next_token=data["next_token"]
            )

    def cache_paper(
        self,
        paper_id: str,
        source: str,
        paper: Paper,
        ttl_hours: Optional[int] = None
    ) -> None:
        """Cache a paper."""
        cache_key = self._generate_cache_key("paper", source, paper_id)
        ttl = ttl_hours or self.default_ttl_hours * 2  # Papers change less frequently
        expires_at = datetime.now() + timedelta(hours=ttl)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO paper_cache
                (cache_key, paper_id, source, paper_data, created_at, expires_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                paper_id,
                source,
                paper.model_dump_json(),
                datetime.now().isoformat(),
                expires_at.isoformat(),
                datetime.now().isoformat()
            ))

        logger.debug(f"Cached paper id='{paper_id}', source='{source}'")

    def get_cached_paper(self, paper_id: str, source: str) -> Optional[Paper]:
        """Retrieve a cached paper."""
        cache_key = self._generate_cache_key("paper", source, paper_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT paper_data, expires_at FROM paper_cache
                WHERE cache_key = ?
            """, (cache_key,))

            row = cursor.fetchone()
            if not row:
                return None

            paper_data, expires_at = row

            if self._is_expired(expires_at):
                conn.execute("DELETE FROM paper_cache WHERE cache_key = ?", (cache_key,))
                return None

            self._update_hit_count("paper_cache", cache_key)

            logger.debug(f"Cache hit for paper id='{paper_id}', source='{source}'")
            return Paper(**json.loads(paper_data))

    def cache_citations(
        self,
        paper_id: str,
        source: str,
        citations: List[Paper],
        ttl_hours: Optional[int] = None
    ) -> None:
        """Cache citation data."""
        cache_key = self._generate_cache_key("citations", source, paper_id)
        ttl = ttl_hours or self.default_ttl_hours
        expires_at = datetime.now() + timedelta(hours=ttl)

        # Convert papers to JSON-serializable format using Pydantic's JSON mode
        citations_data = [paper.model_dump(mode='json') for paper in citations]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO citation_cache
                (cache_key, paper_id, source, citation_data, created_at, expires_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                paper_id,
                source,
                json.dumps(citations_data),
                datetime.now().isoformat(),
                expires_at.isoformat(),
                datetime.now().isoformat()
            ))

        logger.debug(f"Cached {len(citations)} citations for paper id='{paper_id}', source='{source}'")

    def get_cached_citations(self, paper_id: str, source: str) -> Optional[List[Paper]]:
        """Retrieve cached citations."""
        cache_key = self._generate_cache_key("citations", source, paper_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT citation_data, expires_at FROM citation_cache
                WHERE cache_key = ?
            """, (cache_key,))

            row = cursor.fetchone()
            if not row:
                return None

            citation_data, expires_at = row

            if self._is_expired(expires_at):
                conn.execute("DELETE FROM citation_cache WHERE cache_key = ?", (cache_key,))
                return None

            self._update_hit_count("citation_cache", cache_key)

            citations_data = json.loads(citation_data)
            citations = [Paper(**paper_data) for paper_data in citations_data]

            logger.debug(f"Cache hit for citations of paper id='{paper_id}', source='{source}' ({len(citations)} citations)")
            return citations

    def clean_expired_entries(self) -> Dict[str, int]:
        """Remove all expired cache entries and return counts."""
        now = datetime.now().isoformat()
        counts = {}

        with sqlite3.connect(self.db_path) as conn:
            # Clean search cache
            cursor = conn.execute("DELETE FROM search_cache WHERE expires_at < ?", (now,))
            counts["search_cache"] = cursor.rowcount

            # Clean paper cache
            cursor = conn.execute("DELETE FROM paper_cache WHERE expires_at < ?", (now,))
            counts["paper_cache"] = cursor.rowcount

            # Clean citation cache
            cursor = conn.execute("DELETE FROM citation_cache WHERE expires_at < ?", (now,))
            counts["citation_cache"] = cursor.rowcount

        total_removed = sum(counts.values())
        if total_removed > 0:
            logger.info(f"Cleaned {total_removed} expired cache entries: {counts}")

        return counts

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Search cache stats
            cursor = conn.execute("""
                SELECT COUNT(*), SUM(hit_count),
                       COUNT(CASE WHEN expires_at > ? THEN 1 END) as active_count
                FROM search_cache
            """, (datetime.now().isoformat(),))
            total, hits, active = cursor.fetchone()
            stats["search_cache"] = {"total": total, "active": active, "hits": hits or 0}

            # Paper cache stats
            cursor = conn.execute("""
                SELECT COUNT(*), SUM(hit_count),
                       COUNT(CASE WHEN expires_at > ? THEN 1 END) as active_count
                FROM paper_cache
            """, (datetime.now().isoformat(),))
            total, hits, active = cursor.fetchone()
            stats["paper_cache"] = {"total": total, "active": active, "hits": hits or 0}

            # Citation cache stats
            cursor = conn.execute("""
                SELECT COUNT(*), SUM(hit_count),
                       COUNT(CASE WHEN expires_at > ? THEN 1 END) as active_count
                FROM citation_cache
            """, (datetime.now().isoformat(),))
            total, hits, active = cursor.fetchone()
            stats["citation_cache"] = {"total": total, "active": active, "hits": hits or 0}

        return stats

    def clear_all_cache(self) -> None:
        """Clear all cached data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM search_cache")
            conn.execute("DELETE FROM paper_cache")
            conn.execute("DELETE FROM citation_cache")

        logger.info("Cleared all cache data")


# Global cache manager instance
cache_manager = CacheManager()