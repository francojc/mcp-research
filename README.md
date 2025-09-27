# MCP Research Server

An MCP server for academic bibliographic search across multiple sources including arXiv, Semantic Scholar, and more.

## Features

- **Multi-source Academic Search**: Search across arXiv, Semantic Scholar, and Google Scholar
- **Advanced Search Engine**: Field-specific searches with filters for title, author, abstract, venue, and date ranges
- **Unified Bibliographic Format**: Consistent data structure across all sources
- **Export Capabilities**: Export to BibTeX, RIS, and CSL-JSON formats
- **Citation Analysis**: Track citations and paper relationships
- **Intelligent Deduplication**: Advanced algorithms to identify and merge duplicate papers
- **Paper Recommendations**: Content-based, citation-based, and hybrid recommendation systems
- **Zotero Integration**: Seamless integration with Zotero for reference management
- **Performance Optimization**: Built-in caching and rate limiting
- **Query Builder**: Natural language to advanced search query conversion

## Installation

```bash
uv sync
```

## Configuration

Set environment variables for API keys:

```bash
# Required for Semantic Scholar enhanced features
export SEMANTIC_SCHOLAR_API_KEY="your_api_key"

# Optional: Zotero integration (for reference management)
export ZOTERO_USER_ID="your_zotero_user_id"
export ZOTERO_API_KEY="your_zotero_api_key"
```

### Getting API Keys

**Semantic Scholar API Key:**
1. Visit [Semantic Scholar API](https://api.semanticscholar.org/)
2. Register for an API key to access enhanced rate limits

**Zotero API Key:**
1. Go to [Zotero Settings](https://www.zotero.org/settings/keys)
2. Create a new private key with read and write permissions
3. Your User ID can be found in your Zotero profile URL

## Usage with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
   "mcp-research": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/francojc/.local/mcp/mcp-research",
        "server.py"
      ],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "your_api_key",
        "ZOTERO_USER_ID": "your_zotero_user_id",
        "ZOTERO_API_KEY": "your_zotero_api_key"
    }
  }
}
```

## Available Tools

### Core Search Tools

- **`search_papers`**: Search for academic papers across multiple sources
  - Supports advanced syntax (title:"term", author:name, etc.)
  - Multiple sorting options (relevance, date, citations, impact)
  - Automatic deduplication and ranking

- **`advanced_search_papers`**: Field-specific search with granular filters
  - Search by title, author, abstract, venue, keywords
  - Date range filtering (year_start, year_end)
  - Enhanced relevance scoring

- **`search_author_papers`**: Find papers by specific authors
  - Cross-source author search
  - Automatic deduplication of author works

### Paper Information

- **`get_paper_details`**: Get comprehensive information about a specific paper
  - Full metadata, abstracts, and citation counts
  - Support for arXiv and Semantic Scholar IDs

- **`get_citations`**: Analyze citation networks
  - Find papers that cite a given work
  - Citation metrics and analysis

### Export and Bibliography

- **`export_bibliography`**: Export papers in standard formats
  - BibTeX, RIS, and CSL-JSON support
  - Batch export capabilities

### Smart Features

- **`recommend_papers`**: Get intelligent paper recommendations
  - Content-based recommendations
  - Citation-based recommendations
  - Hybrid recommendation methods

- **`build_search_query`**: Convert natural language to advanced search queries
  - Query optimization suggestions
  - Advanced syntax guidance

### Zotero Integration

- **`add_to_zotero`**: Add papers to your Zotero library
  - Automatic metadata conversion
  - Intelligent tagging (source, category, venue)
  - Collection management
  - Duplicate detection and handling

- **`create_zotero_collection`**: Create and manage Zotero collections
  - Support for nested collections (e.g., "Research/AI/Transformers")
  - Automatic organization

- **`list_zotero_collections`**: Browse your Zotero library
  - Filter by collection name
  - Show item counts and MCP-added papers
  - Hierarchical collection display

### System Management

- **`manage_cache`**: Optimize performance with cache management
  - View cache statistics
  - Clean expired entries
  - Clear cache when needed

## Zotero Integration

The MCP Research Server provides seamless integration with Zotero for reference management. This allows you to automatically add discovered papers to your Zotero library with intelligent tagging and organization.

### Setup

1. **Get your Zotero credentials:**
   - **User ID**: Found in your Zotero profile URL (`https://www.zotero.org/users/YOUR_USER_ID`)
   - **API Key**: Create at [Zotero Settings > API Keys](https://www.zotero.org/settings/keys)
     - Select "Allow library access" and "Allow write access"
     - Choose "Personal library" for individual use

2. **Configure environment variables:**
   ```bash
   export ZOTERO_USER_ID="your_user_id"
   export ZOTERO_API_KEY="your_api_key"
   ```

### Features

- **Automatic Metadata Import**: Papers are converted to proper Zotero items with full bibliographic data
- **Intelligent Tagging**: Automatic tags based on:
  - Source (arxiv, semantic-scholar, etc.)
  - Research categories
  - Publication venues
  - Custom user tags
- **Collection Management**: Organize papers into collections, including nested collections
- **Duplicate Detection**: Automatically detects existing papers by DOI, arXiv ID, or title similarity
- **Batch Operations**: Add multiple papers at once from search results

### Usage Examples

```javascript
// Add papers from a search to a collection
add_to_zotero({
  papers: "machine learning transformers",
  collection_name: "Research/AI/Transformers",
  tag_papers: "important,review-needed",
  create_collection: true
})

// Create a new collection structure
create_zotero_collection({
  collection_name: "Research/Linguistics/Corpus Studies",
  description: "Papers related to corpus linguistics research"
})

// List all collections with MCP papers
list_zotero_collections({
  show_mcp_items_only: true,
  show_items_count: true
})
```

## Advanced Search Capabilities

The server includes a sophisticated search engine that goes beyond simple keyword matching:

### Field-Specific Search

Use the `advanced_search_papers` tool for precise control:

```javascript
advanced_search_papers({
  title: "neural machine translation",
  author: "sutskever",
  venue: "nature",
  year_start: 2020,
  year_end: 2024,
  max_results: 20
})
```

### Query Builder

The `build_search_query` tool helps convert natural language descriptions into optimized search queries:

```javascript
build_search_query({
  description: "I'm looking for recent papers about large language models in healthcare applications",
  include_advanced_syntax: true
})
```

### Advanced Search Syntax

- **`title:"exact phrase"`** - Search in titles only
- **`author:lastname`** - Find papers by specific author
- **`abstract:keyword`** - Search in abstracts
- **`venue:"journal name"`** - Search in specific venues
- **`"exact phrase"`** - Search for exact phrases
- **`term1 AND term2`** - Both terms must appear
- **`term1 OR term2`** - Either term can appear
- **`-unwanted`** - Exclude terms (Google Scholar only)

## Paper Recommendations

Get intelligent paper recommendations using the `recommend_papers` tool:

### Recommendation Methods

- **Content-based**: Recommendations based on paper content similarity
- **Citation-based**: Recommendations based on citation networks
- **Hybrid**: Combines multiple signals for better recommendations

### Usage

```javascript
recommend_papers({
  seed_paper_titles: "Attention Is All You Need, BERT: Pre-training of Deep Bidirectional Transformers",
  method: "hybrid",
  max_recommendations: 15,
  sources: "arxiv,semantic_scholar"
})
```

## Cache Management

The server includes an intelligent caching system for improved performance:

### Cache Types

- **Search Cache**: Stores search results to avoid repeated API calls
- **Paper Cache**: Caches detailed paper information
- **Citation Cache**: Stores citation data

### Management Commands

```javascript
// View cache statistics
manage_cache({ action: "stats" })

// Clean expired entries
manage_cache({ action: "clean" })

// Clear all cache data
manage_cache({ action: "clear" })
```
