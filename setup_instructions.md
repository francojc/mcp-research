# MCP Research Server Setup Instructions

## Prerequisites

- Python 3.10 or higher
- Claude Desktop application
- (Optional) Semantic Scholar API key for higher rate limits

## Installation Steps

### 1. Install Dependencies

```bash
cd mcp-research
uv sync
```

Or if you prefer to install manually:
```bash
uv add mcp httpx pydantic feedparser python-dateutil
```

### 2. Get Semantic Scholar API Key (Optional)

1. Visit https://www.semanticscholar.org/product/api
2. Sign up for an account and request an API key
3. Copy your API key

### 3. Configure Claude Desktop

#### Method 1: Manual Configuration

1. Open Claude Desktop
2. Go to Settings > Developer
3. Click "Edit Config" to open `claude_desktop_config.json`
4. Add the server configuration:

```json
{
  "mcpServers": {
    "mcp-research": {
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/Users/francojc/.local/mcp/mcp-research",
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "your_actual_api_key_here"
      }
    }
  }
}
```

5. Replace `/Users/francojc/.local/mcp/mcp-research` with the actual path to your project directory
6. Replace `your_actual_api_key_here` with your Semantic Scholar API key (or remove the env section if not using)

#### Method 2: Copy Configuration File

```bash
# Copy the example configuration
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Edit the file to add your API key and correct paths
```

### 4. Restart Claude Desktop

Close and reopen Claude Desktop. You should see an MCP indicator in the bottom-right corner of the conversation input.

## Testing the Installation

Try these commands in Claude Desktop:

1. **Search for papers:**
   ```
   Search for papers about "machine learning transformers" using the academic search tools
   ```

2. **Get paper details:**
   ```
   Get details for a specific arXiv paper
   ```

3. **Export bibliography:**
   ```
   Export the search results in BibTeX format
   ```

## Troubleshooting

### Server Not Starting

1. Check the Claude Desktop logs (Settings > Developer > View Logs)
2. Verify uv is available: `which uv`
3. Test the server manually:
   ```bash
   cd mcp-research
   uv run server.py
   ```

### API Rate Limits

- arXiv: 3-second delay between requests (built-in)
- Semantic Scholar: 100 requests per 5 minutes (free tier)
- Consider getting a Semantic Scholar API key for higher limits

### No Results Found

1. Check your internet connection
2. Try simpler search terms
3. Check API service status

## Available Tools

- `search_papers`: Search across arXiv and Semantic Scholar
- `get_paper_details`: Get detailed information about a paper
- `get_citations`: Get papers that cite a given paper
- `export_bibliography`: Export papers in BibTeX, RIS, or CSL-JSON format
- `search_author_papers`: Find papers by a specific author

## API Usage Notes

- **arXiv**: No authentication required, rate limited to prevent abuse
- **Semantic Scholar**: Optional API key, higher limits with authentication
- **Google Scholar**: Not implemented (no official API)
- **RefSeek**: Not implemented (API availability unknown)