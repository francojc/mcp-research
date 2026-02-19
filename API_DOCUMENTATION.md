# MCP Research Server API Documentation

## Overview

The MCP Research Server provides comprehensive academic bibliographic search capabilities across multiple sources including arXiv, Semantic Scholar, and Google Scholar. It offers intelligent caching, advanced search features, AI-powered recommendations, robust error handling, and seamless Zotero integration with automatic tagging.

## Table of Contents

- [Installation & Setup](#installation--setup)
- [MCP Tools](#mcp-tools)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Caching System](#caching-system)
- [Health Monitoring](#health-monitoring)
- [Advanced Features](#advanced-features)

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- `uv` package manager
- Claude Desktop application

### Installation

1. Clone or download the MCP Research Server
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure in Claude Desktop (`claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "mcp-research": {
         "command": "uv",
         "args": ["run", "--directory", "/path/to/mcp-research", "server.py"],
         "env": {
           "SEMANTIC_SCHOLAR_API_KEY": "your_api_key_here",
           "ZOTERO_USER_ID": "your_zotero_user_id",
           "ZOTERO_API_KEY": "your_zotero_api_key"
         }
       }
     }
   }
   ```

### API Keys & Credentials

#### Semantic Scholar API Key (Optional but Recommended)

- **Purpose**: Enhanced rate limits and access to premium features
- **How to get**: Visit [Semantic Scholar API](https://www.semanticscholar.org/product/api) and sign up
- **Required**: No, but recommended for heavy usage

#### Zotero API Credentials (Required for Zotero Integration)

- **Purpose**: Add papers directly to your Zotero library with automatic tagging
- **How to get**:
  1. Visit [Zotero Settings](https://www.zotero.org/settings/keys) (requires Zotero account)
  2. Create a new private key with read/write access to your library
  3. Note your User ID (displayed at the top of the keys page)
  4. Copy the generated API key
- **Required**: Only if you want to use Zotero integration tools (`add_to_zotero`, `create_zotero_collection`, `list_zotero_collections`)

#### Environment Variables

If you prefer not to store credentials in the config file, you can set these environment variables:
- `SEMANTIC_SCHOLAR_API_KEY`
- `ZOTERO_USER_ID`
- `ZOTERO_API_KEY`

4. Restart Claude Desktop

## MCP Tools

### 1. search_papers

**Description**: Search for academic papers across multiple sources with intelligent deduplication and ranking.

**Parameters**:

- `query` (string, required): Search query
- `max_results` (integer, default: 10): Maximum number of results to return
- `sources` (string, default: "arxiv,semantic_scholar"): Comma-separated list of sources to search

**Example**:
```
search_papers(
    query="machine learning neural networks",
    max_results=15,
    sources="arxiv,semantic_scholar,google_scholar"
)
```

**Response Format**:

```
Found 15 papers matching your query:

📄 **Paper Title**
👤 Authors: Author1, Author2
📅 Published: 2023-06-15
🏛️ Venue: Conference Name
📊 Citations: 42
🔗 URL: https://example.com/paper
📝 Abstract: Paper abstract...
🏷️ Categories: cs.LG, cs.AI
🔍 Source: arxiv
```

### 2. get_paper_details

**Description**: Get detailed information about a specific paper.

**Parameters**:

- `paper_id` (string, required): Paper identifier (DOI, arXiv ID, or source-specific ID)
- `source` (string, optional): Preferred source to search ("arxiv", "semantic_scholar", "google_scholar")

**Example**:

```
get_paper_details(
    paper_id="2306.12345",
    source="arxiv"
)
```

### 3. get_citations

**Description**: Get papers that cite a specific paper.

**Parameters**:

- `paper_id` (string, required): Paper identifier
- `source` (string, default: "semantic_scholar"): Source to get citations from
- `max_results` (integer, default: 10): Maximum citations to retrieve

**Example**:

```
get_citations(
    paper_id="10.1234/example.doi",
    source="semantic_scholar",
    max_results=20
)
```

### 4. export_bibliography

**Description**: Export papers to various bibliography formats.

**Parameters**:

- `papers` (string, required): Comma-separated paper IDs or search query
- `format` (string, default: "bibtex"): Export format ("bibtex", "ris", "csl_json")
- `output_file` (string, optional): File path to save export

**Supported Formats**:

- `bibtex`: BibTeX format for LaTeX
- `ris`: RIS format for reference managers
- `csl_json`: Citation Style Language JSON

**Example**:
```
export_bibliography(
    papers="2306.12345,10.1234/example",
    format="bibtex",
    output_file="/path/to/bibliography.bib"
)
```

### 5. search_author_papers

**Description**: Find papers by a specific author across multiple sources.

**Parameters**:

- `author_name` (string, required): Author name to search for
- `max_results` (integer, default: 10): Maximum papers to retrieve
- `sources` (string, default: "arxiv,semantic_scholar"): Sources to search

**Example**:

```
search_author_papers(
    author_name="Geoffrey Hinton",
    max_results=25,
    sources="arxiv,semantic_scholar,google_scholar"
)
```

### 6. manage_cache

**Description**: Manage the caching system for improved performance.

**Parameters**:

- `action` (string, required): Action to perform ("stats", "cleanup", "clear")

**Actions**:

- `stats`: Show cache statistics
- `cleanup`: Remove expired cache entries
- `clear`: Clear all cached data

**Example**:
```
manage_cache(action="stats")
```

**Stats Response**:
```
📊 **Cache Statistics**

📈 **Performance**
• Total entries: 1,247
• Cache hits: 892 (71.5%)
• Cache misses: 355 (28.5%)

💾 **Storage**
• Total size: 15.3 MB
• Average entry size: 12.6 KB

🔄 **Activity**
• Entries added today: 127
• Expired entries cleaned: 45
```

### 7. advanced_search_papers

**Description**: Perform advanced search with field-specific queries and date filtering.

**Parameters**:
- `title` (string, optional): Search in paper titles
- `author` (string, optional): Search by author name
- `abstract` (string, optional): Search in abstracts
- `venue` (string, optional): Search by venue/journal
- `keywords` (string, optional): General keyword search
- `year_start` (integer, optional): Start year for date filtering
- `year_end` (integer, optional): End year for date filtering
- `sources` (string, default: "arxiv,semantic_scholar"): Sources to search
- `max_results` (integer, default: 10): Maximum results per source

**Example**:
```
advanced_search_papers(
    title="neural networks",
    author="lecun",
    year_start=2020,
    year_end=2023,
    sources="arxiv,semantic_scholar",
    max_results=15
)
```

### 8. recommend_papers

**Description**: Get AI-powered paper recommendations based on seed papers or interests.

**Parameters**:
- `seed_papers` (string, required): Paper IDs or search query to base recommendations on
- `method` (string, default: "hybrid"): Recommendation method ("content", "citations", "hybrid")
- `max_recommendations` (integer, default: 10): Number of recommendations
- `sources` (string, default: "arxiv,semantic_scholar"): Sources for candidate papers

**Recommendation Methods**:
- `content`: Based on content similarity (titles, abstracts, categories)
- `citations`: Based on citation patterns and popularity
- `hybrid`: Combines content, citations, collaboration, recency, and venue similarity

**Example**:
```
recommend_papers(
    seed_papers="attention is all you need",
    method="hybrid",
    max_recommendations=8,
    sources="arxiv,semantic_scholar"
)
```

**Response Format**:
```
🎯 **Paper Recommendations** (Hybrid Method)

📄 **Recommended Paper Title**
👤 Authors: Author Name
📊 Recommendation Score: 85%
  • Content Similarity: 72%
  • Citation Score: 63%
  • Recency Score: 91%
  • Venue Match: 45%
```

### 9. build_search_query

**Description**: Build optimized search queries from natural language descriptions.

**Parameters**:
- `natural_language` (string, required): Natural language description of what you're looking for
- `target_source` (string, default: "arxiv"): Target source to optimize query for

**Example**:
```
build_search_query(
    natural_language="Find recent papers about transformers in computer vision by researchers at Stanford",
    target_source="arxiv"
)
```

**Response Format**:
```
🔍 **Optimized Search Query**

**For arXiv**:
`ti:"transformer" AND ti:"computer vision" AND au:"stanford" AND submittedDate:[2023-01-01 TO *]`

**Breakdown**:
• Title search: "transformer", "computer vision"
• Author affiliation: "stanford"
• Date filter: From 2023 onwards
• Boolean operators: AND for required terms

**Alternative Queries**:
• Broader: `(transformer OR attention) AND "computer vision"`
• Narrower: `"vision transformer" AND au:"stanford" AND cat:cs.CV`
```

### 10. add_to_zotero

**Description**: Add papers to Zotero library with comprehensive automatic tagging.

**Parameters**:
- `papers` (string, required): Comma-separated paper IDs or search query to find papers
- `collection_name` (string, optional): Name of Zotero collection (supports nested like "Research/AI")
- `create_collection` (boolean, default: true): Whether to create collection if it doesn't exist
- `tag_papers` (string, optional): Comma-separated additional tags to apply to papers
- `auto_tag_source` (boolean, default: true): Whether to automatically tag papers with their source

**Automatic Tagging**: Every paper gets tagged with:
- `mcp-research` (universal tracking tag)
- `source-[arxiv|semantic_scholar|google_scholar]` (source identification)
- `category-[cs.AI|cs.LG|etc]` (subject categories from paper)
- `venue-[conference-or-journal-name]` (publication venue)
- User-specified tags

**Example**:
```
add_to_zotero(
    papers="attention is all you need, BERT pretraining",
    collection_name="PhD Research/Transformers",
    tag_papers="seminal, must-read, chapter-2",
    create_collection=true
)
```

**Response Format**:
```
📚 **Zotero Integration Results**

✅ **Successfully added**: 2 papers
📁 **Collection**: PhD Research/Transformers
🏷️ **Additional Tags**: seminal, must-read, chapter-2
🏷️ **Auto Tags**: mcp-research + source tags

✅ **Attention Is All You Need**
   • Status: Created
   • Zotero URL: https://www.zotero.org/users/12345/items/ABC123

✅ **BERT: Pre-training of Deep Bidirectional Transformers**
   • Status: Created
   • Zotero URL: https://www.zotero.org/users/12345/items/DEF456
```

### 11. create_zotero_collection

**Description**: Create a new collection in Zotero library with support for nested hierarchies.

**Parameters**:
- `collection_name` (string, required): Name of collection (supports nested like "Research/AI/Transformers")
- `parent_collection` (string, optional): Name of parent collection (if not using nested naming)
- `description` (string, optional): Optional description for the collection

**Example**:
```
create_zotero_collection(
    collection_name="PhD Research/Literature Review/Transformers",
    description="Papers about transformer architecture and applications"
)
```

**Response Format**:
```
✅ **Collection Created Successfully**

📁 **Name**: PhD Research/Literature Review/Transformers
🔑 **Key**: ABC123XYZ
🔧 **Type**: nested
🔗 **Zotero URL**: https://www.zotero.org/users/12345/collections/ABC123XYZ
```

### 12. list_zotero_collections

**Description**: List collections in Zotero library with optional filtering and MCP statistics.

**Parameters**:
- `show_items_count` (boolean, default: true): Whether to show item counts for each collection
- `search_filter` (string, optional): Optional filter to search collection names
- `show_mcp_items_only` (boolean, default: false): Whether to show only collections with MCP-added papers

**Example**:
```
list_zotero_collections(
    show_items_count=true,
    search_filter="research",
    show_mcp_items_only=false
)
```

**Response Format**:
```
📚 **Zotero Collections**

Found 5 collections:

📁 **PhD Research** (25 papers, 15 from MCP)
  📁 **Literature Review** (12 papers, 8 from MCP)
    📁 **Transformers** (8 papers, 5 from MCP)
  📁 **Methodology** (6 papers, 3 from MCP)
📁 **Side Projects** (7 papers, 4 from MCP)

📊 **MCP Research Server Statistics**
• Total papers added via MCP: 32
• Recent additions (this month): 8
• Top sources: arxiv(18), semantic_scholar(12), google_scholar(2)
```

## Data Models

### Paper

```python
class Paper:
    id: str                           # Unique identifier
    title: str                        # Paper title
    authors: List[Author]             # List of authors
    abstract: str                     # Paper abstract
    published_date: datetime          # Publication date
    url: str                          # Primary URL
    doi: str                          # Digital Object Identifier
    arxiv_id: str                     # arXiv identifier
    venue: str                        # Journal/conference name
    categories: List[str]             # Subject categories
    citation_count: int               # Number of citations
    source: str                       # Data source
```

### Author

```python
class Author:
    name: str                         # Author name
    affiliation: str                  # Institution affiliation
    author_id: str                    # Source-specific author ID
```

### SearchResult

```python
class SearchResult:
    papers: List[Paper]               # List of found papers
    total_count: int                  # Total papers matching query
    query: str                        # Original search query
    source: str                       # Source that provided results
```

## Error Handling

The system includes comprehensive error handling with user-friendly messages and recovery suggestions.

### Error Categories

- **Network Errors**: Connection timeouts, refused connections
- **API Errors**: Rate limits, service unavailability, authentication issues
- **Parsing Errors**: Invalid JSON, malformed data
- **Validation Errors**: Invalid queries, missing parameters
- **Cache Errors**: Cache system issues

### Error Response Format

```
❌ **Error**: Description of what went wrong

💡 **Suggestions**:
• Specific suggestion 1
• Specific suggestion 2
• Contact support if issue persists

⏱️ **Recommended wait time**: 30 seconds
```

### Automatic Recovery

- **Exponential Backoff**: Automatic retry with increasing delays
- **Circuit Breaker**: Prevents cascade failures by temporarily disabling failing services
- **Graceful Degradation**: Continue with available sources when others fail

## Caching System

### Cache Types

1. **Search Cache**: Stores search results (TTL: 1 hour)
2. **Paper Cache**: Stores individual paper details (TTL: 24 hours)
3. **Citations Cache**: Stores citation lists (TTL: 6 hours)

### Cache Features

- **Automatic Expiration**: TTL-based cache invalidation
- **Intelligent Deduplication**: Prevents redundant API calls
- **Statistics Tracking**: Hit/miss ratios and performance metrics
- **Manual Management**: Tools for cleanup and clearing

### Cache Statistics

```python
{
    "total_entries": 1247,
    "cache_hits": 892,
    "cache_misses": 355,
    "hit_rate": 0.715,
    "total_size_mb": 15.3,
    "entries_by_type": {
        "search": 445,
        "papers": 678,
        "citations": 124
    }
}
```

## Health Monitoring

### Monitored Services

- **arXiv API**: Research paper database
- **Semantic Scholar API**: Academic search engine
- **Google Scholar**: Web-based academic search
- **Cache System**: Internal caching layer

### Health Status Levels

- **Healthy**: Service operating normally
- **Degraded**: Service available but experiencing issues
- **Unhealthy**: Service having significant problems
- **Down**: Service unavailable
- **Unknown**: Status cannot be determined

### Health Check Features

- **Continuous Monitoring**: Automatic health checks at regular intervals
- **Circuit Breaker Integration**: Prevents calls to failing services
- **Response Time Tracking**: Monitor service performance
- **Uptime Statistics**: Calculate availability percentages

## Advanced Features

### Deduplication Algorithm

Intelligent paper deduplication using multiple criteria:

1. **DOI Matching**: Exact DOI comparison
2. **arXiv ID Matching**: arXiv identifier comparison
3. **Fuzzy Title Matching**: Similarity-based title comparison (>90% threshold)
4. **Author Overlap**: Shared author detection
5. **Venue Similarity**: Conference/journal name matching

### Ranking System

Multi-factor paper ranking considering:

- **Relevance Score**: Query term matching and TF-IDF
- **Citation Score**: Logarithmic citation count scaling
- **Recency Score**: Publication date weighting
- **Completeness Score**: Data field availability
- **Source Reliability**: Source-specific quality factors

### Recommendation Algorithms

#### Content-Based Recommendations
- Keyword extraction and similarity matching
- Category overlap analysis
- Abstract semantic similarity

#### Citation-Based Recommendations
- Co-citation analysis
- Reference pattern matching
- Citation velocity tracking

#### Hybrid Recommendations
- Weighted combination of all factors
- Collaborative filtering elements
- Trending paper detection

### Query Optimization

Automatic query enhancement for different sources:

- **arXiv**: Field-specific prefixes (ti:, au:, abs:, cat:)
- **Semantic Scholar**: Author-specific queries and filtering
- **Google Scholar**: Boolean operators and field modifiers

## Rate Limiting & Best Practices

### API Rate Limits

- **arXiv**: 3 requests per second
- **Semantic Scholar**: 100 requests per minute (with API key)
- **Google Scholar**: Conservative scraping with delays

### Best Practices

1. **Use Caching**: Enable caching for better performance
2. **Batch Requests**: Combine related queries when possible
3. **Specific Queries**: Use field-specific searches for better results
4. **Error Handling**: Always handle potential API failures
5. **Rate Respect**: Don't exceed recommended request rates

## Troubleshooting

### Common Issues

#### "Rate limit exceeded"
- **Cause**: Too many requests in short time period
- **Solution**: Wait for rate limit reset, reduce request frequency
- **Prevention**: Use caching, batch operations

#### "Service unavailable"
- **Cause**: Academic database temporarily down
- **Solution**: Try alternative sources, wait and retry
- **Prevention**: Enable multiple sources for redundancy

#### "No results found"
- **Cause**: Query too specific or no matching papers
- **Solution**: Broaden search terms, check spelling
- **Prevention**: Use query building tool for optimization

#### "Cache errors"
- **Cause**: Cache database issues
- **Solution**: Clear cache, restart server
- **Prevention**: Regular cache maintenance

### Debug Information

Enable detailed logging by setting log level to DEBUG in the server configuration. This provides:

- Request/response details
- Cache hit/miss information
- Error stack traces
- Performance metrics

## API Versioning

Current API version: **1.0**

The API follows semantic versioning principles:
- **Major**: Breaking changes requiring client updates
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes, no functional changes

## Support & Contributing

### Getting Help

1. Check this documentation first
2. Review error messages and suggestions
3. Check service health status
4. Enable debug logging for detailed information

### Reporting Issues

When reporting issues, include:
- Error messages and stack traces
- Query details and parameters used
- Service health status
- Steps to reproduce the problem

### Performance Optimization Tips

1. **Use appropriate max_results**: Don't request more papers than needed
2. **Leverage caching**: Repeated queries use cached results
3. **Batch operations**: Combine related searches when possible
4. **Field-specific searches**: Use targeted searches for better performance
5. **Monitor service health**: Check for degraded services before making requests
