# MCP Research Server Setup Guide

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Configure Claude Desktop** by editing `claude_desktop_config.json`:
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

3. **Restart Claude Desktop**

## Detailed Configuration

### Basic Setup (No API Keys Required)

The server works without any API keys, but with limited functionality:

- arXiv search (unlimited, no key needed)
- Google Scholar search (rate limited)
- Basic paper details and citations

### Enhanced Setup (Recommended)

#### Semantic Scholar API Key

Provides enhanced rate limits and premium features.

**Get your key**:

1. Visit https://www.semanticscholar.org/product/api
2. Sign up for a free account
3. Generate an API key
4. Add to your configuration

**Benefits**:
- Higher rate limits
- Access to advanced paper metadata
- Improved search results quality

#### Zotero Integration Setup
Enables direct integration with your Zotero library.

**Get your credentials**:
1. **Create Zotero account** (if you don't have one):
   - Visit https://www.zotero.org/user/register

2. **Generate API key**:
   - Go to https://www.zotero.org/settings/keys
   - Click "Create new private key"
   - Give it a descriptive name (e.g., "MCP Research Server")
   - Enable all permissions:
     - ✅ Allow library access
     - ✅ Allow write access
   - Click "Save key"

3. **Get your User ID**:
   - On the same page, your User ID is displayed at the top
   - It's a number like `12345678`

4. **Add to configuration**:
   ```json
   "env": {
     "ZOTERO_USER_ID": "12345678",
     "ZOTERO_API_KEY": "abc123def456..."
   }
   ```

**What you can do with Zotero integration**:
- Add papers directly to your Zotero library
- Organize papers in collections
- Automatic tagging with `mcp-research` tag
- Batch import of search results

## Configuration Examples

### Minimal Configuration
```json
{
  "mcpServers": {
    "mcp-research": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-research", "server.py"]
    }
  }
}
```

### With Semantic Scholar Only
```json
{
  "mcpServers": {
    "mcp-research": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-research", "server.py"],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "your_semantic_scholar_key"
      }
    }
  }
}
```

### Full Configuration
```json
{
  "mcpServers": {
    "mcp-research": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-research", "server.py"],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "your_semantic_scholar_key",
        "ZOTERO_USER_ID": "your_user_id",
        "ZOTERO_API_KEY": "your_zotero_key"
      }
    }
  }
}
```

## Testing Your Setup

### 1. Test Basic Functionality
```
Search for "transformer neural networks" in recent machine learning papers
```

### 2. Test Semantic Scholar Integration
If you have a Semantic Scholar API key, try:
```
Get detailed information about paper with DOI: 10.1038/nature14539
```

### 3. Test Zotero Integration
If you have Zotero credentials configured:
```
Create a new Zotero collection called "AI Research"
```
```
List my Zotero collections
```

## Troubleshooting

### Server Won't Start
- Check that the path in your config matches your actual installation directory
- Ensure `uv` is installed and available in your PATH
- Verify Python 3.10+ is installed

### API Key Issues
- **Semantic Scholar**: Verify your key is valid at https://api.semanticscholar.org/graph/v1/paper/batch
- **Zotero**: Test your credentials at https://api.zotero.org/users/YOUR_USER_ID/items (replace YOUR_USER_ID)

### Zotero Integration Issues
- Ensure your API key has write permissions enabled
- Check that your User ID is correct (numeric, not username)
- Verify your Zotero library is accessible online

### Rate Limiting
- Google Scholar may temporarily block requests if used heavily
- Semantic Scholar rate limits are much higher with an API key
- Zotero has generous rate limits for personal use

## Environment Variables (Recommended for Security)

**For better security**, store credentials as environment variables instead of in the config file. This prevents accidental exposure of API keys in configuration files.

### Setup Environment Variables

#### Option 1: Current Session Only
```bash
export SEMANTIC_SCHOLAR_API_KEY="your_key_here"
export ZOTERO_USER_ID="your_user_id"
export ZOTERO_API_KEY="your_api_key"
```

#### Option 2: Persistent (Recommended)
Add to your shell profile (`~/.zshrc`, `~/.bashrc`, or `~/.profile`):
```bash
# MCP Research Server Credentials
export SEMANTIC_SCHOLAR_API_KEY="your_semantic_scholar_key"
export ZOTERO_USER_ID="your_zotero_user_id"
export ZOTERO_API_KEY="your_zotero_api_key"
```

Then restart your terminal and Claude Desktop.

### Minimal Config File
With environment variables set, use this minimal config:
```json
{
  "mcpServers": {
    "mcp-research": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-research", "server.py"]
    }
  }
}
```

### How It Works
The MCP Research Server now loads configuration with this precedence:

1. Existing process environment variables (including values passed via the
   Claude Desktop `env` block).
2. `.env` file in the project directory (loaded non-overriding).
3. Built-in defaults: free Semantic Scholar access (no API key) and Zotero
   disabled.

This means values you set in Claude Desktop’s `env` or your shell take
priority; the `.env` file only fills in anything missing.

### Benefits of Environment Variables
- ✅ **Security**: Credentials not exposed in config files
- ✅ **Version Control**: Safe to commit config files to git
- ✅ **Flexibility**: Easy to change credentials without editing config
- ✅ **Best Practice**: Industry standard for credential management

## Security Notes

- Keep your API keys secure and never commit them to version control
- Use environment variables for production deployments
- Zotero API keys have fine-grained permissions - only enable what you need
- All API communications use HTTPS encryption
