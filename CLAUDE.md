# mcp-research

MCP server for academic paper search across arXiv, Semantic Scholar, and
Google Scholar, with Zotero library integration.

## Commands

```bash
uv sync                       # install/update dependencies
uv sync --extra dev           # include dev tools (pytest, black, ruff)
uv run pytest tests/          # run test suite
uv run black --check .        # check formatting
uv run ruff check .           # lint
uv run python server.py       # run server directly (stdio transport)
uv run python smoke_test.py   # connectivity check against live APIs
```

## Architecture

Flat module layout — all source files live at the repo root (no `src/`
package). The entry point is `server.py`, which registers MCP tools via
`FastMCP` and wires up the client modules.

Key modules:

- `server.py` — MCP tool definitions, client initialization, `main()`
- `arxiv_client.py` — arXiv Atom API client
- `semantic_scholar_client.py` — Semantic Scholar REST client
- `google_scholar_client.py` — Google Scholar HTML scraper (module-level
  singleton `google_scholar_client`)
- `zotero_client.py` — Zotero API via pyzotero; requires `ZOTERO_USER_ID`
  and `ZOTERO_API_KEY`
- `models.py` — Pydantic data models (`Paper`, `Author`, `SearchResult`)
- `cache_manager.py` — SQLite cache (`cache.db` at repo root)
- `deduplication.py`, `ranking.py` — post-search processing
- `advanced_search.py` — field-specific query builder
- `recommendation_system.py` — seed-paper recommendations
- `export_utils.py` — BibTeX/RIS/CSL-JSON export

Tests live in `tests/` and use `pytest-asyncio`.

## Dependencies

Managed with `uv` (lockfile: `uv.lock`). No `flake.nix`. The project
uses `hatchling` as its build backend (`pyproject.toml`). Python >=3.10.

## Configuration

Environment variables (set via MCP config or shell; `.env` is loaded but
never overrides existing env vars):

- `ZOTERO_USER_ID` / `ZOTERO_API_KEY` — optional; Zotero tools degrade
  gracefully when missing
- Semantic Scholar and arXiv need no API keys for basic use

Precedence: existing env (including MCP-passed vars) > `.env` > defaults.

The server runs over **stdio** transport (standard MCP pattern). Tool
registration uses the `@mcp.tool()` decorator from `FastMCP`.

## Known gotchas

- **Flat imports**: all modules import each other with bare names
  (`from models import Paper`), not package-qualified paths. Adding a
  package directory would break every import.
- **google_scholar singleton**: `google_scholar_client.py` exports a
  module-level instance named `google_scholar_client` (same name as the
  module). Import it by name: `from google_scholar_client import
  google_scholar_client`.
- **Soft Zotero init**: `ZoteroClient.__init__` raises `ValueError` when
  credentials are missing. `setup_clients()` in `server.py` catches this
  and sets `zotero_client = None`; all Zotero tools check for `None`
  before proceeding.
- **cache.db persistence**: `CacheManager` creates `cache.db` in the
  working directory on import (module-level singleton). The file is
  gitignored but will appear locally after first run.
- **`.env` non-override**: `load_dotenv(override=False)` means `.env`
  values never replace variables already in the environment. If an MCP
  host passes env vars, those win.
- **Line length**: `black` and `ruff` are configured for 80 chars
  (`pyproject.toml`), but `ruff` ignores E501.
