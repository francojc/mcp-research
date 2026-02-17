"""Integration tests for MCP server tool functions.

These tests call the tool functions defined in server.py directly,
after patching the module-level client globals.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock, MagicMock
from datetime import datetime

from models import Paper, Author, SearchResult
import server


class TestServerTools:
    """Tests for the @mcp.tool()-decorated functions in server.py."""

    @pytest.fixture
    def mock_paper(self):
        return Paper(
            id="tool-test-1",
            title="Tool Test Paper",
            authors=[Author(name="Tool Author")],
            abstract="Abstract for tool testing.",
            published_date=datetime(2023, 6, 15),
            url="https://example.com/paper",
            doi="10.1234/tool",
            citation_count=10,
            source="arxiv",
            source_id="tool-test-1",
            arxiv_id="2306.00001",
            venue="Tool Conference",
            categories=["cs.LG"],
        )

    @pytest.fixture
    def mock_search_result(self, mock_paper):
        return SearchResult(
            papers=[mock_paper],
            total_count=1,
            query="test",
            source="arxiv",
        )

    @pytest.fixture(autouse=True)
    def _patch_clients(self, mock_paper, mock_search_result):
        """Patch module-level clients for all tests."""
        mock_arxiv = AsyncMock()
        mock_arxiv.search.return_value = mock_search_result
        mock_arxiv.get_paper_by_id.return_value = mock_paper
        mock_arxiv.search_by_author.return_value = mock_search_result

        mock_ss = AsyncMock()
        mock_ss.search.return_value = mock_search_result
        mock_ss.get_paper_by_id.return_value = mock_paper
        mock_ss.get_citations.return_value = [mock_paper]
        mock_ss.search_by_author.return_value = mock_search_result

        with (
            patch.object(server, "arxiv_client", mock_arxiv),
            patch.object(server, "semantic_scholar_client", mock_ss),
            patch.object(server, "zotero_client", None),
        ):
            yield

    # -- search_papers --

    @pytest.mark.asyncio
    async def test_search_papers_returns_results(self):
        """search_papers returns formatted text with paper info."""
        result = await server.search_papers(
            query="machine learning",
            sources="arxiv",
            max_results=5,
        )
        assert "Found" in result
        assert "Tool Test Paper" in result
        assert "Tool Author" in result

    @pytest.mark.asyncio
    async def test_search_papers_empty(self):
        """search_papers with no results."""
        empty = SearchResult(
            papers=[], total_count=0, query="nothing", source="arxiv"
        )
        server.arxiv_client.search.return_value = empty

        result = await server.search_papers(
            query="nothing", sources="arxiv"
        )
        assert "Found 0 papers" in result

    @pytest.mark.asyncio
    async def test_search_papers_error_handling(self):
        """search_papers catches per-source exceptions and continues.

        When a single source fails, the tool logs the error and
        returns whatever results it got from other sources (which
        may be zero).  It does not propagate the exception.
        """
        server.arxiv_client.search.side_effect = Exception("boom")

        result = await server.search_papers(
            query="test", sources="arxiv"
        )
        # The tool swallows per-source errors and returns results
        assert "Found 0 papers" in result

    # -- get_paper_details --

    @pytest.mark.asyncio
    async def test_get_paper_details_arxiv(self):
        """get_paper_details returns paper info for arXiv source."""
        result = await server.get_paper_details(
            paper_id="2306.00001", source="arxiv"
        )
        assert "Tool Test Paper" in result
        assert "Tool Author" in result

    @pytest.mark.asyncio
    async def test_get_paper_details_not_found(self):
        """get_paper_details reports when paper is missing."""
        server.arxiv_client.get_paper_by_id.return_value = None

        result = await server.get_paper_details(
            paper_id="nonexistent", source="arxiv"
        )
        assert "not found" in result.lower()

    # -- get_citations --

    @pytest.mark.asyncio
    async def test_get_citations(self):
        """get_citations returns citing papers."""
        result = await server.get_citations(
            paper_id="target", source="semantic_scholar"
        )
        assert "citing" in result.lower() or "Tool Test Paper" in result

    @pytest.mark.asyncio
    async def test_get_citations_none(self):
        """get_citations with no results."""
        server.semantic_scholar_client.get_citations.return_value = []

        result = await server.get_citations(
            paper_id="lonely", source="semantic_scholar"
        )
        assert "no citing" in result.lower() or "not found" in result.lower()

    # -- search_author_papers --

    @pytest.mark.asyncio
    async def test_search_author_papers(self):
        """search_author_papers returns results."""
        result = await server.search_author_papers(
            author_name="Tool Author", sources="arxiv"
        )
        assert "Tool Test Paper" in result

    # -- manage_cache --

    @pytest.mark.asyncio
    async def test_manage_cache_stats(self):
        """manage_cache stats action returns statistics."""
        with patch.object(server, "cache_manager") as mock_cm:
            mock_cm.get_cache_stats.return_value = {
                "search_cache": {
                    "total": 10,
                    "active": 8,
                    "hits": 5,
                },
                "paper_cache": {
                    "total": 20,
                    "active": 15,
                    "hits": 10,
                },
                "citation_cache": {
                    "total": 5,
                    "active": 3,
                    "hits": 2,
                },
            }
            result = await server.manage_cache(action="stats")
            assert "Cache Statistics" in result

    @pytest.mark.asyncio
    async def test_manage_cache_clear(self):
        """manage_cache clear action clears data."""
        with patch.object(server, "cache_manager") as mock_cm:
            result = await server.manage_cache(action="clear")
            assert "cleared" in result.lower()
            mock_cm.clear_all_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_cache_invalid_action(self):
        """manage_cache with invalid action reports error."""
        result = await server.manage_cache(action="invalid")
        assert "invalid" in result.lower()

    # -- Zotero tools (client is None) --

    @pytest.mark.asyncio
    async def test_add_to_zotero_not_configured(self):
        """add_to_zotero reports unavailable when client is None."""
        result = await server.add_to_zotero(papers="test query")
        assert "not available" in result.lower()

    @pytest.mark.asyncio
    async def test_create_zotero_collection_not_configured(self):
        """create_zotero_collection reports unavailable."""
        result = await server.create_zotero_collection(
            collection_name="Test"
        )
        assert "not available" in result.lower()

    @pytest.mark.asyncio
    async def test_list_zotero_collections_not_configured(self):
        """list_zotero_collections reports unavailable."""
        result = await server.list_zotero_collections()
        assert "not available" in result.lower()
