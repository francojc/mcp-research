"""Integration tests for MCP tools."""

import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime

from server import app
from models import Paper, Author, SearchResult


class TestMCPTools:
    """Integration tests for MCP tools."""

    @pytest.fixture
    def mock_search_result(self):
        """Mock search result for testing."""
        papers = [
            Paper(
                id="test-paper-1",
                title="Test Machine Learning Paper",
                authors=[Author(name="John Doe", affiliation="Test University")],
                abstract="This is a test paper about machine learning algorithms.",
                published_date=datetime(2023, 6, 15),
                url="https://arxiv.org/abs/2306.12345",
                doi="10.1234/test.paper",
                arxiv_id="2306.12345",
                venue="Test Conference on AI",
                categories=["cs.LG", "cs.AI"],
                citation_count=42,
                source="arxiv"
            ),
            Paper(
                id="test-paper-2",
                title="Advanced Deep Learning Techniques",
                authors=[Author(name="Jane Smith", affiliation="Example Corp")],
                abstract="This paper explores advanced techniques in deep learning.",
                published_date=datetime(2023, 5, 20),
                url="https://arxiv.org/abs/2305.98765",
                doi="10.1234/test.paper2",
                arxiv_id="2305.98765",
                venue="Deep Learning Journal",
                categories=["cs.LG", "cs.NE"],
                citation_count=28,
                source="semantic_scholar"
            )
        ]
        return SearchResult(
            papers=papers,
            total_count=2,
            query="machine learning",
            source="multiple"
        )

    @pytest.mark.asyncio
    async def test_search_papers_basic(self, mock_search_result):
        """Test basic search_papers functionality."""
        with patch('server.search_and_deduplicate') as mock_search:
            mock_search.return_value = mock_search_result

            result = await app.call_tool("search_papers", {
                "query": "machine learning",
                "max_results": 2,
                "sources": "arxiv,semantic_scholar"
            })

            assert "Found 2 papers" in result
            assert "Test Machine Learning Paper" in result
            assert "Advanced Deep Learning Techniques" in result
            assert "John Doe" in result
            assert "Jane Smith" in result

    @pytest.mark.asyncio
    async def test_search_papers_no_results(self):
        """Test search_papers with no results."""
        empty_result = SearchResult(papers=[], total_count=0, query="nonexistent", source="arxiv")

        with patch('server.search_and_deduplicate') as mock_search:
            mock_search.return_value = empty_result

            result = await app.call_tool("search_papers", {
                "query": "nonexistent topic",
                "max_results": 10
            })

            assert "No papers found" in result

    @pytest.mark.asyncio
    async def test_search_papers_error_handling(self):
        """Test search_papers error handling."""
        with patch('server.search_and_deduplicate') as mock_search:
            mock_search.side_effect = Exception("API Error")

            result = await app.call_tool("search_papers", {
                "query": "test",
                "max_results": 10
            })

            assert "Error" in result or "failed" in result

    @pytest.mark.asyncio
    async def test_get_paper_details_success(self):
        """Test get_paper_details with successful retrieval."""
        mock_paper = Paper(
            id="detailed-paper-1",
            title="Detailed Paper Information",
            authors=[Author(name="Detail Author", affiliation="Detail University")],
            abstract="This paper provides detailed information for testing.",
            published_date=datetime(2023, 7, 1),
            url="https://example.com/paper",
            doi="10.1234/detailed",
            citation_count=15,
            source="semantic_scholar"
        )

        with patch('server.get_paper_from_multiple_sources') as mock_get:
            mock_get.return_value = mock_paper

            result = await app.call_tool("get_paper_details", {
                "paper_id": "detailed-paper-1",
                "source": "semantic_scholar"
            })

            assert "Detailed Paper Information" in result
            assert "Detail Author" in result
            assert "15 citations" in result

    @pytest.mark.asyncio
    async def test_get_paper_details_not_found(self):
        """Test get_paper_details when paper not found."""
        with patch('server.get_paper_from_multiple_sources') as mock_get:
            mock_get.return_value = None

            result = await app.call_tool("get_paper_details", {
                "paper_id": "nonexistent-paper",
                "source": "arxiv"
            })

            assert "not found" in result or "No paper" in result

    @pytest.mark.asyncio
    async def test_get_citations_success(self):
        """Test get_citations functionality."""
        mock_citations = [
            Paper(
                id="citing-paper-1",
                title="Paper That Cites Original",
                authors=[Author(name="Citing Author")],
                abstract="This paper cites the original work.",
                citation_count=5,
                source="semantic_scholar"
            )
        ]

        with patch('server.get_citations_from_sources') as mock_get:
            mock_get.return_value = mock_citations

            result = await app.call_tool("get_citations", {
                "paper_id": "original-paper",
                "source": "semantic_scholar",
                "max_results": 10
            })

            assert "Found 1 citing papers" in result
            assert "Paper That Cites Original" in result
            assert "Citing Author" in result

    @pytest.mark.asyncio
    async def test_export_bibliography_bibtex(self, mock_search_result):
        """Test bibliography export in BibTeX format."""
        with patch('server.search_and_deduplicate') as mock_search:
            mock_search.return_value = mock_search_result

            result = await app.call_tool("export_bibliography", {
                "papers": "test-paper-1,test-paper-2",
                "format": "bibtex",
                "output_file": "/tmp/test_export.bib"
            })

            assert "Bibliography exported" in result
            assert "BibTeX" in result

    @pytest.mark.asyncio
    async def test_export_bibliography_invalid_format(self):
        """Test bibliography export with invalid format."""
        result = await app.call_tool("export_bibliography", {
            "papers": "test-paper-1",
            "format": "invalid_format"
        })

        assert "Error" in result or "Unsupported" in result

    @pytest.mark.asyncio
    async def test_search_author_papers(self):
        """Test search_author_papers functionality."""
        mock_papers = [
            Paper(
                id="author-paper-1",
                title="Paper by Specific Author",
                authors=[Author(name="Specific Author", affiliation="University")],
                abstract="This is a paper by the specific author.",
                citation_count=10,
                source="arxiv"
            )
        ]

        with patch('server.search_author_across_sources') as mock_search:
            mock_search.return_value = mock_papers

            result = await app.call_tool("search_author_papers", {
                "author_name": "Specific Author",
                "max_results": 10,
                "sources": "arxiv,semantic_scholar"
            })

            assert "Found 1 papers" in result
            assert "Paper by Specific Author" in result
            assert "Specific Author" in result

    @pytest.mark.asyncio
    async def test_manage_cache_stats(self):
        """Test cache management statistics."""
        with patch('server.cache_manager') as mock_cache:
            mock_cache.get_cache_stats.return_value = {
                "total_entries": 150,
                "cache_hits": 75,
                "cache_misses": 25,
                "hit_rate": 0.75,
                "total_size_mb": 5.2
            }

            result = await app.call_tool("manage_cache", {
                "action": "stats"
            })

            assert "150" in result  # total_entries
            assert "75%" in result or "0.75" in result  # hit_rate
            assert "5.2" in result  # total_size_mb

    @pytest.mark.asyncio
    async def test_manage_cache_cleanup(self):
        """Test cache cleanup functionality."""
        with patch('server.cache_manager') as mock_cache:
            mock_cache.cleanup_expired.return_value = 25

            result = await app.call_tool("manage_cache", {
                "action": "cleanup"
            })

            assert "25" in result
            assert "expired" in result or "cleaned" in result

    @pytest.mark.asyncio
    async def test_advanced_search_papers(self):
        """Test advanced search with field-specific queries."""
        mock_results = {
            "arxiv": SearchResult(
                papers=[Paper(
                    id="advanced-paper-1",
                    title="Advanced Search Result",
                    authors=[Author(name="Advanced Author")],
                    abstract="Result from advanced search.",
                    source="arxiv"
                )],
                total_count=1,
                query="advanced search",
                source="arxiv"
            )
        }

        with patch('server.advanced_search_engine') as mock_engine:
            mock_engine.search_by_fields.return_value = mock_results

            result = await app.call_tool("advanced_search_papers", {
                "title": "neural networks",
                "author": "smith",
                "year_start": 2020,
                "year_end": 2023,
                "sources": "arxiv",
                "max_results": 10
            })

            assert "Advanced Search Result" in result
            assert "Advanced Author" in result

    @pytest.mark.asyncio
    async def test_recommend_papers_content_based(self, mock_search_result):
        """Test content-based paper recommendations."""
        from recommendation_system import RecommendationScore

        mock_recommendations = [
            RecommendationScore(
                paper=mock_search_result.papers[0],
                total_score=0.85,
                content_score=0.85,
                citation_score=0.2,
                recency_score=0.1
            )
        ]

        with patch('server.search_and_deduplicate') as mock_search, \
             patch('server.recommendation_system') as mock_rec_system:

            mock_search.return_value = mock_search_result
            mock_rec_system.recommend_similar_papers.return_value = mock_recommendations

            result = await app.call_tool("recommend_papers", {
                "seed_papers": "machine learning",
                "method": "content",
                "max_recommendations": 5
            })

            assert "recommendations" in result
            assert "Test Machine Learning Paper" in result
            assert "85%" in result or "0.85" in result

    @pytest.mark.asyncio
    async def test_build_search_query(self):
        """Test search query building functionality."""
        result = await app.call_tool("build_search_query", {
            "natural_language": "Find papers about machine learning by John Doe published after 2020",
            "target_source": "arxiv"
        })

        # Should contain structured query elements
        assert "machine learning" in result
        assert "John Doe" in result or "author:" in result
        assert "2020" in result

    @pytest.mark.asyncio
    async def test_tool_parameter_validation(self):
        """Test parameter validation for MCP tools."""
        # Test missing required parameter
        result = await app.call_tool("search_papers", {})
        assert "Error" in result or "required" in result

        # Test invalid parameter values
        result = await app.call_tool("search_papers", {
            "query": "",
            "max_results": -1
        })
        # Should handle gracefully

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mock_search_result):
        """Test handling of concurrent tool calls."""
        import asyncio

        with patch('server.search_and_deduplicate') as mock_search:
            mock_search.return_value = mock_search_result

            # Make multiple concurrent calls
            tasks = [
                app.call_tool("search_papers", {"query": f"test {i}", "max_results": 5})
                for i in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # All calls should complete successfully
            assert len(results) == 3
            for result in results:
                assert isinstance(result, str)
                assert len(result) > 0

    @pytest.mark.asyncio
    async def test_tool_error_recovery(self):
        """Test error recovery and graceful degradation."""
        with patch('server.arxiv_client') as mock_arxiv, \
             patch('server.semantic_scholar_client') as mock_ss:

            # Simulate one client failing
            mock_arxiv.search.side_effect = Exception("arXiv unavailable")
            mock_ss.search.return_value = SearchResult(
                papers=[],
                total_count=0,
                query="test",
                source="semantic_scholar"
            )

            result = await app.call_tool("search_papers", {
                "query": "test",
                "sources": "arxiv,semantic_scholar"
            })

            # Should complete even with one source failing
            assert isinstance(result, str)
            # Should indicate partial success or graceful handling

    @pytest.mark.asyncio
    async def test_large_result_handling(self):
        """Test handling of large result sets."""
        # Create a large mock result
        large_papers = [
            Paper(
                id=f"paper-{i}",
                title=f"Paper {i}",
                authors=[Author(name=f"Author {i}")],
                abstract=f"Abstract for paper {i}",
                source="arxiv"
            )
            for i in range(100)
        ]

        large_result = SearchResult(
            papers=large_papers,
            total_count=100,
            query="large test",
            source="arxiv"
        )

        with patch('server.search_and_deduplicate') as mock_search:
            mock_search.return_value = large_result

            result = await app.call_tool("search_papers", {
                "query": "large test",
                "max_results": 50
            })

            # Should handle large results without issues
            assert "Found" in result
            assert len(result) < 50000  # Reasonable size limit for response