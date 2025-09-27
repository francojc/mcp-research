# MCP Research Server

An MCP server for academic bibliographic search across multiple sources including arXiv, Semantic Scholar, and more.

## Features

- Search academic papers across multiple sources
- Unified bibliographic data format
- Export capabilities (BibTeX, RIS, CSL-JSON)
- Citation tracking and paper details
- Rate limiting and caching

## Installation

```bash
uv sync
```

## Configuration

Set environment variables for API keys:

```bash
export SEMANTIC_SCHOLAR_API_KEY="your_api_key"
```

## Usage with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-research": {
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/path/to/mcp-research",
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "your_api_key"
      }
    }
  }
}
```

## Available Tools

- `search_papers`: Search for academic papers
- `get_paper_details`: Get detailed information about a paper
- `get_citations`: Get citation information
- `export_bibliography`: Export papers in various formats
- `search_author_papers`: Search papers by author