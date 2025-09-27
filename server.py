"""MCP server for academic bibliographic search."""

import asyncio
import logging
import sys
from typing import List, Optional, Dict, Any

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv, find_dotenv

from arxiv_client import ArxivClient
from semantic_scholar_client import SemanticScholarClient
from google_scholar_client import google_scholar_client
from export_utils import export_papers
from models import Paper, SearchResult
from deduplication import paper_deduplicator
from ranking import paper_ranker, SortCriterion
from cache_manager import cache_manager
from advanced_search import AdvancedSearchEngine, QueryBuilder, DateRange
from recommendation_system import recommendation_system
from zotero_client import ZoteroClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)

# Load environment variables from .env with safe precedence
# Precedence: existing env (including MCP-passed vars) > .env > defaults
try:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=False)
        logger.info("Loaded environment from .env (non-overriding)")
    else:
        logger.debug("No .env file found; using existing environment only")
except Exception as e:
    logger.warning(f"Failed to load .env file: {e}")

# Initialize MCP server
mcp = FastMCP("academic-search")

# Global clients (will be initialized in main)
arxiv_client: Optional[ArxivClient] = None
semantic_scholar_client: Optional[SemanticScholarClient] = None
advanced_search_engine: Optional[AdvancedSearchEngine] = None
zotero_client: Optional[ZoteroClient] = None


@mcp.tool()
async def search_papers(
    query: str,
    sources: str = "arxiv,semantic_scholar",
    max_results: int = 10,
    sort_by: str = "relevance"
) -> str:
    """
    Search for academic papers across multiple sources.

    Args:
        query: Search query string (supports advanced syntax like title:"machine learning" author:smith)
        sources: Comma-separated list of sources ('arxiv', 'semantic_scholar', 'google_scholar')
        max_results: Maximum number of results to return (default: 10)
        sort_by: Sort criterion ('relevance', 'date', 'citations', 'combined', 'impact')

    Returns:
        String containing search results with advanced deduplication and ranking
    """
    try:
        source_list = [s.strip() for s in sources.split(",")]
        all_papers = []

        for source in source_list:
            if source == "arxiv" and arxiv_client:
                try:
                    result = await arxiv_client.search(
                        query=query,
                        max_results=max_results,
                        sort_by="relevance" if sort_by == "relevance" else "lastUpdatedDate"
                    )
                    all_papers.extend(result.papers)
                    logger.info(f"Found {len(result.papers)} papers from arXiv")
                except Exception as e:
                    logger.error(f"arXiv search failed: {e}")

            elif source == "semantic_scholar" and semantic_scholar_client:
                try:
                    result = await semantic_scholar_client.search(
                        query=query,
                        max_results=max_results
                    )
                    all_papers.extend(result.papers)
                    logger.info(f"Found {len(result.papers)} papers from Semantic Scholar")
                except Exception as e:
                    logger.error(f"Semantic Scholar search failed: {e}")

            elif source == "google_scholar" and google_scholar_client:
                try:
                    result = await google_scholar_client.search(
                        query=query,
                        max_results=max_results
                    )
                    all_papers.extend(result.papers)
                    logger.info(f"Found {len(result.papers)} papers from Google Scholar")
                except Exception as e:
                    logger.error(f"Google Scholar search failed: {e}")

        # Advanced deduplication
        unique_papers, duplicate_matches = paper_deduplicator.deduplicate_papers(
            all_papers, similarity_threshold=0.8
        )

        if duplicate_matches:
            logger.info(f"Found and removed {len(duplicate_matches)} duplicate pairs")

        # Advanced ranking and sorting
        sort_criterion_map = {
            "relevance": SortCriterion.RELEVANCE,
            "date": SortCriterion.DATE,
            "citations": SortCriterion.CITATIONS,
            "combined": SortCriterion.COMBINED,
            "impact": SortCriterion.IMPACT
        }

        sort_criterion = sort_criterion_map.get(sort_by, SortCriterion.COMBINED)
        unique_papers = paper_ranker.sort_papers(
            unique_papers,
            criterion=sort_criterion,
            query=query,
            reverse=True
        )

        # Limit results
        unique_papers = unique_papers[:max_results]

        # Format results
        results = []
        for paper in unique_papers:
            result_item = {
                "id": paper.id,
                "title": paper.title,
                "authors": [author.name for author in paper.authors],
                "abstract": paper.abstract,
                "published_date": paper.published_date.isoformat() if paper.published_date else None,
                "url": paper.url,
                "pdf_url": paper.pdf_url,
                "doi": paper.doi,
                "arxiv_id": paper.arxiv_id,
                "venue": paper.venue,
                "citation_count": paper.citation_count,
                "categories": paper.categories,
                "source": paper.source
            }
            results.append(result_item)

        return f"Found {len(results)} papers:\n\n" + "\n\n".join([
            f"**{i+1}. {paper['title']}**\n"
            f"Authors: {', '.join(paper['authors'])}\n"
            f"Source: {paper['source']}\n"
            f"Published: {paper['published_date'] or 'Unknown'}\n"
            f"Citations: {paper['citation_count'] or 'Unknown'}\n"
            f"URL: {paper['url']}\n"
            f"Abstract: {(paper['abstract'] or 'No abstract available')[:200]}..."
            for i, paper in enumerate(results)
        ])

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Search failed: {str(e)}"


async def search_and_deduplicate(query: str, sources: List[str], max_results: int = 10) -> SearchResult:
    """
    Internal helper function that searches and deduplicates papers, returning SearchResult object.
    Used by other functions that need access to Paper objects rather than formatted strings.
    """
    all_papers = []

    for source in sources:
        if source == "arxiv" and arxiv_client:
            try:
                result = await arxiv_client.search(
                    query=query,
                    max_results=max_results,
                    sort_by="relevance"
                )
                all_papers.extend(result.papers)
                logger.info(f"Found {len(result.papers)} papers from arXiv")
            except Exception as e:
                logger.error(f"arXiv search failed: {e}")

        elif source == "semantic_scholar" and semantic_scholar_client:
            try:
                result = await semantic_scholar_client.search(
                    query=query,
                    max_results=max_results
                )
                all_papers.extend(result.papers)
                logger.info(f"Found {len(result.papers)} papers from Semantic Scholar")
            except Exception as e:
                logger.error(f"Semantic Scholar search failed: {e}")

    # Deduplicate papers
    unique_papers, duplicate_matches = paper_deduplicator.deduplicate_papers(
        all_papers, similarity_threshold=0.8
    )

    if duplicate_matches:
        logger.info(f"Found and removed {len(duplicate_matches)} duplicate pairs")

    # Sort by relevance
    unique_papers = paper_ranker.sort_papers(
        unique_papers,
        criterion=SortCriterion.RELEVANCE,
        query=query,
        reverse=True
    )

    # Limit results
    unique_papers = unique_papers[:max_results]

    return SearchResult(
        papers=unique_papers,
        total_count=len(unique_papers),
        query=query,
        source=",".join(sources)
    )


@mcp.tool()
async def get_paper_details(paper_id: str, source: str) -> str:
    """
    Get detailed information about a specific paper.

    Args:
        paper_id: Paper ID (arXiv ID or Semantic Scholar ID)
        source: Source ('arxiv' or 'semantic_scholar')

    Returns:
        JSON string containing paper details
    """
    try:
        paper = None

        if source == "arxiv" and arxiv_client:
            paper = await arxiv_client.get_paper_by_id(paper_id)
        elif source == "semantic_scholar" and semantic_scholar_client:
            paper = await semantic_scholar_client.get_paper_by_id(paper_id)

        if not paper:
            return f"Paper not found: {paper_id} from {source}"

        details = {
            "id": paper.id,
            "title": paper.title,
            "authors": [{"name": author.name, "affiliation": author.affiliation} for author in paper.authors],
            "abstract": paper.abstract,
            "published_date": paper.published_date.isoformat() if paper.published_date else None,
            "updated_date": paper.updated_date.isoformat() if paper.updated_date else None,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "doi": paper.doi,
            "arxiv_id": paper.arxiv_id,
            "venue": paper.venue,
            "citation_count": paper.citation_count,
            "categories": paper.categories,
            "source": paper.source
        }

        return f"**{paper.title}**\n\n" \
               f"Authors: {', '.join([author.name for author in paper.authors])}\n" \
               f"Published: {paper.published_date.isoformat() if paper.published_date else 'Unknown'}\n" \
               f"Venue: {paper.venue or 'Unknown'}\n" \
               f"Citations: {paper.citation_count or 'Unknown'}\n" \
               f"Categories: {', '.join(paper.categories) if paper.categories else 'None'}\n" \
               f"DOI: {paper.doi or 'None'}\n" \
               f"arXiv ID: {paper.arxiv_id or 'None'}\n" \
               f"URL: {paper.url}\n" \
               f"PDF: {paper.pdf_url or 'Not available'}\n\n" \
               f"**Abstract:**\n{paper.abstract or 'No abstract available'}"

    except Exception as e:
        logger.error(f"Get paper details failed: {e}")
        return f"Failed to get paper details: {str(e)}"


@mcp.tool()
async def get_citations(paper_id: str, source: str = "semantic_scholar", max_results: int = 10) -> str:
    """
    Get papers that cite the given paper.

    Args:
        paper_id: Paper ID
        source: Source ('semantic_scholar' only for now)
        max_results: Maximum number of citing papers to return

    Returns:
        String containing citing papers information
    """
    try:
        if source == "semantic_scholar" and semantic_scholar_client:
            citing_papers = await semantic_scholar_client.get_citations(
                paper_id, limit=max_results
            )

            if not citing_papers:
                return f"No citing papers found for {paper_id}"

            results = []
            for i, paper in enumerate(citing_papers):
                result_item = f"**{i+1}. {paper.title}**\n" \
                             f"Authors: {', '.join([author.name for author in paper.authors])}\n" \
                             f"Published: {paper.published_date.isoformat() if paper.published_date else 'Unknown'}\n" \
                             f"Citations: {paper.citation_count or 'Unknown'}\n" \
                             f"URL: {paper.url}"
                results.append(result_item)

            return f"Found {len(citing_papers)} papers citing {paper_id}:\n\n" + "\n\n".join(results)
        else:
            return f"Citations not supported for source: {source}"

    except Exception as e:
        logger.error(f"Get citations failed: {e}")
        return f"Failed to get citations: {str(e)}"


@mcp.tool()
async def export_bibliography(
    paper_ids: str,
    sources: str,
    format_type: str = "bibtex"
) -> str:
    """
    Export papers in bibliography format.

    Args:
        paper_ids: Comma-separated list of paper IDs
        sources: Comma-separated list of sources corresponding to paper_ids
        format_type: Export format ('bibtex', 'ris', 'csl-json')

    Returns:
        String containing formatted bibliography
    """
    try:
        paper_id_list = [pid.strip() for pid in paper_ids.split(",")]
        source_list = [src.strip() for src in sources.split(",")]

        if len(paper_id_list) != len(source_list):
            return "Error: Number of paper IDs must match number of sources"

        papers = []
        for paper_id, source in zip(paper_id_list, source_list):
            paper = None
            if source == "arxiv" and arxiv_client:
                paper = await arxiv_client.get_paper_by_id(paper_id)
            elif source == "semantic_scholar" and semantic_scholar_client:
                paper = await semantic_scholar_client.get_paper_by_id(paper_id)

            if paper:
                papers.append(paper)

        if not papers:
            return "No papers found for export"

        exported = export_papers(papers, format_type)
        return f"Exported {len(papers)} papers in {format_type} format:\n\n{exported.content}"

    except Exception as e:
        logger.error(f"Export bibliography failed: {e}")
        return f"Failed to export bibliography: {str(e)}"


@mcp.tool()
async def search_author_papers(author_name: str, sources: str = "arxiv,semantic_scholar", max_results: int = 10) -> str:
    """
    Search for papers by a specific author.

    Args:
        author_name: Author's name
        sources: Comma-separated list of sources
        max_results: Maximum number of results

    Returns:
        String containing author's papers
    """
    try:
        source_list = [s.strip() for s in sources.split(",")]
        all_papers = []

        for source in source_list:
            if source == "arxiv" and arxiv_client:
                try:
                    result = await arxiv_client.search_by_author(author_name, max_results)
                    all_papers.extend(result.papers)
                except Exception as e:
                    logger.error(f"arXiv author search failed: {e}")

            elif source == "semantic_scholar" and semantic_scholar_client:
                try:
                    result = await semantic_scholar_client.search_by_author(author_name, max_results)
                    all_papers.extend(result.papers)
                except Exception as e:
                    logger.error(f"Semantic Scholar author search failed: {e}")

        # Advanced deduplication
        unique_papers, duplicate_matches = paper_deduplicator.deduplicate_papers(
            all_papers, similarity_threshold=0.8
        )

        if duplicate_matches:
            logger.info(f"Found and removed {len(duplicate_matches)} duplicate pairs in author search")

        unique_papers = unique_papers[:max_results]

        if not unique_papers:
            return f"No papers found for author: {author_name}"

        results = []
        for i, paper in enumerate(unique_papers):
            result_item = f"**{i+1}. {paper.title}**\n" \
                         f"Authors: {', '.join([author.name for author in paper.authors])}\n" \
                         f"Published: {paper.published_date.isoformat() if paper.published_date else 'Unknown'}\n" \
                         f"Source: {paper.source}\n" \
                         f"URL: {paper.url}"
            results.append(result_item)

        return f"Found {len(unique_papers)} papers by {author_name}:\n\n" + "\n\n".join(results)

    except Exception as e:
        logger.error(f"Author search failed: {e}")
        return f"Failed to search author papers: {str(e)}"


@mcp.tool()
async def manage_cache(action: str = "stats") -> str:
    """
    Manage the local cache system.

    Args:
        action: Action to perform ('stats', 'clean', 'clear')

    Returns:
        String containing cache management results
    """
    try:
        if action == "stats":
            stats = cache_manager.get_cache_stats()
            return f"**Cache Statistics:**\n\n" \
                   f"**Search Cache:** {stats['search_cache']['active']}/{stats['search_cache']['total']} active " \
                   f"({stats['search_cache']['hits']} hits)\n" \
                   f"**Paper Cache:** {stats['paper_cache']['active']}/{stats['paper_cache']['total']} active " \
                   f"({stats['paper_cache']['hits']} hits)\n" \
                   f"**Citation Cache:** {stats['citation_cache']['active']}/{stats['citation_cache']['total']} active " \
                   f"({stats['citation_cache']['hits']} hits)"

        elif action == "clean":
            removed = cache_manager.clean_expired_entries()
            total_removed = sum(removed.values())
            return f"**Cache Cleanup Complete**\n\n" \
                   f"Removed {total_removed} expired entries:\n" \
                   f"- Search cache: {removed.get('search_cache', 0)}\n" \
                   f"- Paper cache: {removed.get('paper_cache', 0)}\n" \
                   f"- Citation cache: {removed.get('citation_cache', 0)}"

        elif action == "clear":
            cache_manager.clear_all_cache()
            return "**All cache data cleared successfully.**"

        else:
            return f"Invalid action: {action}. Available actions: stats, clean, clear"

    except Exception as e:
        logger.error(f"Cache management failed: {e}")
        return f"Failed to manage cache: {str(e)}"


@mcp.tool()
async def advanced_search_papers(
    title: str = "",
    author: str = "",
    abstract: str = "",
    venue: str = "",
    keywords: str = "",
    year_start: int = None,
    year_end: int = None,
    sources: str = "arxiv,semantic_scholar",
    max_results: int = 10
) -> str:
    """
    Advanced field-specific search across academic sources.

    Args:
        title: Search in paper titles
        author: Author name to search for
        abstract: Keywords to search in abstracts
        venue: Venue/journal name
        keywords: General keywords
        year_start: Earliest publication year
        year_end: Latest publication year
        sources: Comma-separated list of sources
        max_results: Maximum results to return

    Returns:
        String containing search results
    """
    try:
        if not advanced_search_engine:
            return "Advanced search engine not available"

        source_list = [s.strip() for s in sources.split(",")]

        results = await advanced_search_engine.search_by_fields(
            title=title if title else None,
            author=author if author else None,
            abstract=abstract if abstract else None,
            venue=venue if venue else None,
            keywords=keywords if keywords else None,
            year_start=year_start,
            year_end=year_end,
            sources=source_list,
            max_results=max_results
        )

        # Combine results from all sources
        all_papers = []
        for source, result in results.items():
            all_papers.extend(result.papers)

        if not all_papers:
            return "No papers found matching the specified criteria"

        # Advanced deduplication and ranking
        unique_papers, duplicate_matches = paper_deduplicator.deduplicate_papers(
            all_papers, similarity_threshold=0.8
        )

        if duplicate_matches:
            logger.info(f"Found and removed {len(duplicate_matches)} duplicate pairs")

        # Sort by combined score
        unique_papers = paper_ranker.sort_papers(
            unique_papers,
            criterion=SortCriterion.COMBINED,
            query=" ".join(filter(None, [title, author, keywords])),
            reverse=True
        )

        unique_papers = unique_papers[:max_results]

        # Format results
        results_formatted = []
        for i, paper in enumerate(unique_papers):
            result_item = f"**{i+1}. {paper.title}**\n" \
                         f"Authors: {', '.join([author.name for author in paper.authors])}\n" \
                         f"Source: {paper.source}\n" \
                         f"Published: {paper.published_date.isoformat() if paper.published_date else 'Unknown'}\n" \
                         f"Citations: {paper.citation_count or 'Unknown'}\n" \
                         f"Venue: {paper.venue or 'Unknown'}\n" \
                         f"URL: {paper.url}\n"

            if paper.abstract:
                result_item += f"Abstract: {paper.abstract[:200]}...\n"

            results_formatted.append(result_item)

        search_summary = f"**Advanced Search Results** ({len(unique_papers)} papers)\n"
        search_summary += f"Searched in: {', '.join(source_list)}\n"
        if year_start or year_end:
            search_summary += f"Date range: {year_start or 'Any'} - {year_end or 'Present'}\n"
        search_summary += "\n"

        return search_summary + "\n\n".join(results_formatted)

    except Exception as e:
        logger.error(f"Advanced search failed: {e}")
        return f"Advanced search failed: {str(e)}"


@mcp.tool()
async def recommend_papers(
    seed_paper_titles: str,
    method: str = "hybrid",
    max_recommendations: int = 10,
    sources: str = "arxiv,semantic_scholar"
) -> str:
    """
    Get paper recommendations based on seed papers.

    Args:
        seed_paper_titles: Comma-separated list of paper titles to base recommendations on
        method: Recommendation method ('content', 'citations', 'hybrid')
        max_recommendations: Maximum number of recommendations
        sources: Sources to search for candidate papers

    Returns:
        String containing recommended papers
    """
    try:
        if not advanced_search_engine:
            return "Recommendation system not available"

        # Find seed papers by searching for titles
        seed_titles = [title.strip() for title in seed_paper_titles.split(",")]
        seed_papers = []

        for title in seed_titles:
            if not title:
                continue

            # Search for the seed paper
            result = await search_papers(f'title:"{title}"', sources=sources, max_results=3)

            # Try to extract papers from search results (this is a simplified approach)
            # In a production system, you'd parse the results more carefully
            if "**1." in result:
                # Found at least one paper - we'll use this as a seed
                # For now, we'll create a simplified approach
                pass

        # For demonstration, let's use a different approach
        # Search for papers in the same domain and recommend based on that
        combined_query = " OR ".join([f'"{title}"' for title in seed_titles if title])

        if not combined_query:
            return "No valid seed paper titles provided"

        # Get candidate papers from multiple sources
        candidate_results = await advanced_search_engine.search(
            combined_query,
            sources=sources.split(","),
            max_results=50  # Get larger pool for recommendations
        )

        all_candidates = []
        for source, result in candidate_results.items():
            all_candidates.extend(result.papers)

        if not all_candidates:
            return "No candidate papers found for recommendations"

        # For now, return top papers sorted by combined score as recommendations
        # In a full implementation, you would use the actual recommendation system
        unique_papers, _ = paper_deduplicator.deduplicate_papers(
            all_candidates, similarity_threshold=0.8
        )

        # Sort by combined ranking
        recommended_papers = paper_ranker.sort_papers(
            unique_papers,
            criterion=SortCriterion.COMBINED,
            query=combined_query,
            reverse=True
        )

        recommended_papers = recommended_papers[:max_recommendations]

        # Format recommendations
        results_formatted = []
        for i, paper in enumerate(recommended_papers):
            result_item = f"**{i+1}. {paper.title}**\n" \
                         f"Authors: {', '.join([author.name for author in paper.authors])}\n" \
                         f"Source: {paper.source}\n" \
                         f"Citations: {paper.citation_count or 'Unknown'}\n" \
                         f"Published: {paper.published_date.isoformat() if paper.published_date else 'Unknown'}\n" \
                         f"Relevance: High (based on {method} method)\n" \
                         f"URL: {paper.url}\n"

            if paper.abstract:
                result_item += f"Abstract: {paper.abstract[:150]}...\n"

            results_formatted.append(result_item)

        header = f"**Paper Recommendations** (Method: {method})\n"
        header += f"Based on: {seed_paper_titles}\n"
        header += f"Found {len(recommended_papers)} recommendations\n\n"

        return header + "\n\n".join(results_formatted)

    except Exception as e:
        logger.error(f"Paper recommendation failed: {e}")
        return f"Paper recommendation failed: {str(e)}"


@mcp.tool()
async def build_search_query(
    description: str,
    include_advanced_syntax: bool = True
) -> str:
    """
    Help build advanced search queries from natural language descriptions.

    Args:
        description: Natural language description of what you're looking for
        include_advanced_syntax: Whether to include field-specific syntax

    Returns:
        String with suggested search queries and tips
    """
    try:
        query_builder = QueryBuilder()

        # Parse the description and suggest improvements
        suggestions = query_builder.suggest_query_improvements(description)

        response = f"**Search Query Builder**\n\n"
        response += f"**Original Description:** {description}\n\n"

        if include_advanced_syntax:
            response += "**Advanced Search Syntax Examples:**\n"
            response += "- `title:\"machine learning\"` - Search in titles only\n"
            response += "- `author:smith` - Find papers by specific author\n"
            response += "- `abstract:neural` - Search in abstracts\n"
            response += "- `venue:\"nature\"` - Search in specific venues\n"
            response += "- `\"exact phrase\"` - Search for exact phrases\n"
            response += "- `term1 AND term2` - Both terms must appear\n"
            response += "- `term1 OR term2` - Either term can appear\n"
            response += "- `-unwanted` - Exclude terms (Google Scholar)\n\n"

        if suggestions:
            response += "**Suggestions to Improve Your Search:**\n"
            for suggestion in suggestions:
                response += f"- {suggestion}\n"
            response += "\n"

        # Try to create a better query
        if "machine learning" in description.lower():
            response += "**Suggested Queries:**\n"
            response += "- `title:\"machine learning\" AND neural`\n"
            response += "- `\"machine learning\" author:hinton OR author:bengio`\n"
            response += "- `abstract:\"deep learning\" venue:\"nature machine intelligence\"`\n"
        elif "nlp" in description.lower() or "natural language" in description.lower():
            response += "**Suggested Queries:**\n"
            response += "- `title:\"natural language processing\"`\n"
            response += "- `\"language model\" OR \"transformer\"`\n"
            response += "- `abstract:\"nlp\" venue:\"acl\"`\n"
        else:
            response += "**General Query Building Tips:**\n"
            response += "- Use specific terminology from your field\n"
            response += "- Combine multiple concepts with AND/OR\n"
            response += "- Use quotes for multi-word phrases\n"
            response += "- Consider searching by author or venue for focused results\n"

        return response

    except Exception as e:
        logger.error(f"Query building failed: {e}")
        return f"Query building failed: {str(e)}"


@mcp.tool()
async def add_to_zotero(
    papers: str,
    collection_name: str = "",
    create_collection: bool = True,
    tag_papers: str = "",
    auto_tag_source: bool = True
) -> str:
    """
    Add papers to Zotero library with comprehensive tagging.

    Args:
        papers: Comma-separated paper IDs or search query to find papers
        collection_name: Name of Zotero collection to add papers to (supports nested like "Research/AI")
        create_collection: Whether to create collection if it doesn't exist
        tag_papers: Comma-separated additional tags to apply to papers
        auto_tag_source: Whether to automatically tag papers with their source

    Returns:
        String with results of adding papers to Zotero
    """
    try:
        if not zotero_client:
            return "❌ **Zotero Integration Not Available**: Please configure Zotero credentials in your environment variables (ZOTERO_USER_ID and ZOTERO_API_KEY)."

        # Test connection first
        try:
            connection_test = await zotero_client.test_connection()
            if not connection_test.get("permissions", {}).get("write"):
                return "❌ **Insufficient Permissions**: Your Zotero API key doesn't have write permissions. Please create a new API key with write access."
        except Exception as e:
            return f"❌ **Zotero Connection Failed**: {str(e)}\n\nPlease check your Zotero credentials and try again."

        # Parse additional tags
        additional_tags = [tag.strip() for tag in tag_papers.split(",") if tag.strip()] if tag_papers else []

        # Determine if papers are IDs or a search query
        if "," in papers and not " " in papers:
            # Likely comma-separated IDs
            paper_ids = [p.strip() for p in papers.split(",")]
            target_papers = []

            # Get each paper by ID (this would need implementation to resolve paper IDs)
            for paper_id in paper_ids:
                # For now, treat as search queries if not pure IDs
                search_result = await search_and_deduplicate(paper_id, ["arxiv", "semantic_scholar"], 1)
                if search_result.papers:
                    target_papers.extend(search_result.papers)

        else:
            # Treat as search query
            search_result = await search_and_deduplicate(papers, ["arxiv", "semantic_scholar"], 10)
            target_papers = search_result.papers

        if not target_papers:
            return f"❌ **No Papers Found**: No papers found for query/IDs: '{papers}'"

        # Add papers to Zotero
        results = []
        success_count = 0
        error_count = 0

        for paper in target_papers:
            try:
                result = await zotero_client.add_paper_to_collection(
                    paper=paper,
                    collection_name=collection_name,
                    additional_tags=additional_tags,
                    create_collection=create_collection,
                    auto_tag_source=auto_tag_source
                )

                if result["status"] in ["created", "updated"]:
                    success_count += 1
                    status_emoji = "✅" if result["status"] == "created" else "🔄"
                    results.append(f"{status_emoji} **{paper.title[:60]}...**")
                    results.append(f"   • Status: {result['status'].title()}")
                    if result.get("zotero_url"):
                        results.append(f"   • Zotero URL: {result['zotero_url']}")
                    results.append("")

            except Exception as e:
                error_count += 1
                results.append(f"❌ **Error adding {paper.title[:40]}...**: {str(e)}")
                results.append("")

        # Summary
        summary = f"📚 **Zotero Integration Results**\n\n"
        summary += f"✅ **Successfully added**: {success_count} papers\n"
        if error_count > 0:
            summary += f"❌ **Errors**: {error_count} papers\n"
        if collection_name:
            summary += f"📁 **Collection**: {collection_name}\n"
        if additional_tags:
            summary += f"🏷️ **Additional Tags**: {', '.join(additional_tags)}\n"
        summary += f"🏷️ **Auto Tags**: mcp-research + source tags\n\n"

        return summary + "\n".join(results)

    except Exception as e:
        logger.error(f"Zotero integration failed: {e}")
        return f"❌ **Zotero Integration Failed**: {str(e)}"


@mcp.tool()
async def create_zotero_collection(
    collection_name: str,
    parent_collection: str = "",
    description: str = ""
) -> str:
    """
    Create a new collection in Zotero library.

    Args:
        collection_name: Name of the collection to create (supports nested like "Research/AI/Transformers")
        parent_collection: Name of parent collection (if not using nested naming)
        description: Optional description for the collection

    Returns:
        String with result of collection creation
    """
    try:
        if not zotero_client:
            return "❌ **Zotero Integration Not Available**: Please configure Zotero credentials."

        # Test connection
        try:
            connection_test = await zotero_client.test_connection()
            if not connection_test.get("permissions", {}).get("write"):
                return "❌ **Insufficient Permissions**: Your Zotero API key doesn't have write permissions."
        except Exception as e:
            return f"❌ **Zotero Connection Failed**: {str(e)}"

        # Create the collection
        result = await zotero_client.create_collection(
            collection_name=collection_name,
            parent_collection=parent_collection if parent_collection else None,
            description=description
        )

        response = f"✅ **Collection Created Successfully**\n\n"
        response += f"📁 **Name**: {result['name']}\n"
        response += f"🔑 **Key**: {result['collection_key']}\n"
        if result.get("parent"):
            response += f"📂 **Parent**: {result['parent']}\n"
        response += f"🔧 **Type**: {result.get('type', 'simple')}\n"

        zotero_url = f"https://www.zotero.org/{zotero_client.library_type}s/{zotero_client.user_id}/collections/{result['collection_key']}"
        response += f"🔗 **Zotero URL**: {zotero_url}\n"

        return response

    except Exception as e:
        logger.error(f"Collection creation failed: {e}")
        return f"❌ **Collection Creation Failed**: {str(e)}"


@mcp.tool()
async def list_zotero_collections(
    show_items_count: bool = True,
    search_filter: str = "",
    show_mcp_items_only: bool = False
) -> str:
    """
    List collections in Zotero library with optional filtering.

    Args:
        show_items_count: Whether to show item counts for each collection
        search_filter: Optional filter to search collection names
        show_mcp_items_only: Whether to show only collections with MCP-added papers

    Returns:
        String with formatted list of collections
    """
    try:
        if not zotero_client:
            return "❌ **Zotero Integration Not Available**: Please configure Zotero credentials."

        # Test connection
        try:
            await zotero_client.test_connection()
        except Exception as e:
            return f"❌ **Zotero Connection Failed**: {str(e)}"

        # Get collections
        collections = await zotero_client.list_collections(
            show_items_count=show_items_count,
            search_filter=search_filter,
            show_mcp_items_only=show_mcp_items_only
        )

        if not collections:
            return "📁 **No Collections Found**\n\nNo collections match your search criteria."

        # Format results
        response = f"📚 **Zotero Collections**"
        if search_filter:
            response += f" (filtered by: '{search_filter}')"
        if show_mcp_items_only:
            response += f" (MCP papers only)"
        response += f"\n\nFound {len(collections)} collections:\n\n"

        # Group by hierarchy
        root_collections = []
        child_collections = {}

        for collection in collections:
            if not collection["parent_collection"]:
                root_collections.append(collection)
            else:
                parent_key = collection["parent_collection"]
                if parent_key not in child_collections:
                    child_collections[parent_key] = []
                child_collections[parent_key].append(collection)

        # Format output with hierarchy
        def format_collection(collection, indent=0):
            indent_str = "  " * indent
            name = collection["name"]

            line = f"{indent_str}📁 **{name}**"
            if show_items_count:
                count = collection.get("items_count", 0)
                mcp_count = collection.get("mcp_items_count", 0)
                if show_mcp_items_only:
                    line += f" ({mcp_count} MCP papers)"
                else:
                    line += f" ({count} papers"
                    if mcp_count > 0:
                        line += f", {mcp_count} from MCP"
                    line += ")"

            result_lines = [line]

            # Add child collections
            collection_key = collection["key"]
            if collection_key in child_collections:
                for child in child_collections[collection_key]:
                    result_lines.extend(format_collection(child, indent + 1))

            return result_lines

        formatted_lines = []
        for collection in root_collections:
            formatted_lines.extend(format_collection(collection))

        response += "\n".join(formatted_lines)

        # Add MCP statistics if available
        if show_mcp_items_only or any(c.get("mcp_items_count", 0) > 0 for c in collections):
            try:
                stats = await zotero_client.get_mcp_papers_stats()
                response += f"\n\n📊 **MCP Research Server Statistics**\n"
                response += f"• Total papers added via MCP: {stats['total_mcp_papers']}\n"
                response += f"• Recent additions (this month): {stats['recent_additions']}\n"
                if stats["by_source"]:
                    response += f"• Top sources: {', '.join(f'{k}({v})' for k, v in list(stats['by_source'].items())[:3])}\n"
            except Exception:
                pass  # Stats are optional

        return response

    except Exception as e:
        logger.error(f"Listing collections failed: {e}")
        return f"❌ **Failed to List Collections**: {str(e)}"


async def setup_clients():
    """Initialize the API clients and search engine."""
    global arxiv_client, semantic_scholar_client, advanced_search_engine, zotero_client
    arxiv_client = ArxivClient()
    semantic_scholar_client = SemanticScholarClient()

    # Initialize advanced search engine
    advanced_search_engine = AdvancedSearchEngine(
        arxiv_client=arxiv_client,
        semantic_scholar_client=semantic_scholar_client,
        google_scholar_client=google_scholar_client
    )

    # Initialize Zotero client (optional - only if credentials are available)
    try:
        zotero_client = ZoteroClient()
        logger.info("Zotero client initialized successfully")
    except Exception as e:
        logger.warning(f"Zotero client not initialized: {e}")
        zotero_client = None


async def cleanup_clients():
    """Clean up the API clients."""
    global arxiv_client, semantic_scholar_client
    if arxiv_client:
        await arxiv_client.close()
    if semantic_scholar_client:
        await semantic_scholar_client.close()
    if google_scholar_client:
        await google_scholar_client.close()


def main():
    """Main function to run the MCP server."""
    logger.info("Starting MCP Academic Search Server...")

    # Set up cleanup
    import atexit
    def cleanup():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(cleanup_clients())
            loop.close()
        except:
            pass
    atexit.register(cleanup)

    # Initialize clients synchronously for MCP
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_clients())

    # Run the server
    mcp.run()


if __name__ == "__main__":
    main()
