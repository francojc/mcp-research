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

1. **Clone the repository:**

```bash
git clone https://github.com/francojc/mcp-research.git
cd mcp-research
```

2. **Install dependencies:**

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

### Usage Through Claude

Once configured, you can use these tools through Claude Desktop by making natural language requests:

**Adding papers to Zotero:**

> "Search for papers about machine learning transformers and add them to a new Zotero collection called 'Research/AI/Transformers' with the tags 'important' and 'review-needed'"

**Managing collections:**

> "Create a new Zotero collection called 'Research/Linguistics/Corpus Studies' for my corpus linguistics research"

**Browsing your library:**

> "Show me all my Zotero collections and how many papers I've added through MCP Research"

The MCP server will automatically call the appropriate tools (`add_to_zotero`, `create_zotero_collection`, `list_zotero_collections`) based on your requests.

## Advanced Search Capabilities

The server includes a sophisticated search engine that goes beyond simple keyword matching:

### Field-Specific Search

You can request advanced searches through natural language:

> "Find papers with 'neural machine translation' in the title, authored by Sutskever, published in Nature between 2020 and 2024"

Claude will use the `advanced_search_papers` tool to perform precise field-specific searches.

### Query Builder

Ask Claude to help optimize your search queries:

> "Help me build a search query to find recent papers about large language models in healthcare applications"

Claude will use the `build_search_query` tool to suggest optimized search terms and syntax.

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

### Usage Through Claude

Request recommendations using natural language:

> "Based on the papers 'Attention Is All You Need' and 'BERT: Pre-training of Deep Bidirectional Transformers', recommend 15 similar papers using hybrid recommendation methods"

Claude will use the `recommend_papers` tool to find relevant papers using content-based, citation-based, or hybrid approaches.

## Cache Management

The server includes an intelligent caching system for improved performance:

### Cache Types

- **Search Cache**: Stores search results to avoid repeated API calls
- **Paper Cache**: Caches detailed paper information
- **Citation Cache**: Stores citation data

### Management Through Claude

You can manage the cache system through natural language requests:

> "Show me the cache statistics for the MCP Research server"

> "Clean up expired cache entries to improve performance"

> "Clear all cached data and start fresh"

Claude will use the `manage_cache` tool with the appropriate actions (stats, clean, clear) based on your requests.
