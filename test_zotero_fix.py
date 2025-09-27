#!/usr/bin/env python3
"""Test the fixed add_to_zotero functionality."""

import asyncio
import sys
import os

# Add current directory to path to import server modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import add_to_zotero
from server import arxiv_client, semantic_scholar_client, zotero_client
from arxiv_client import ArxivClient
from semantic_scholar_client import SemanticScholarClient
from zotero_client import ZoteroClient

async def test_add_to_zotero_fix():
    """Test the fixed add_to_zotero functionality."""
    print("🧪 Testing Fixed add_to_zotero...")
    print("=" * 50)

    try:
        # Initialize global clients (simulating server startup)
        import server
        if not server.arxiv_client:
            server.arxiv_client = ArxivClient()
        if not server.semantic_scholar_client:
            server.semantic_scholar_client = SemanticScholarClient()
        if not server.zotero_client:
            server.zotero_client = ZoteroClient()

        print("✅ Clients initialized")

        # Test adding a paper with a simple search
        print("\n📄 Testing paper search and add to Zotero...")
        search_query = "attention is all you need"
        add_result = await add_to_zotero(
            papers=search_query,
            collection_name="MCP-Research-Test-Fixed",
            tag_papers="test-fix,transformer",
            auto_tag_source=True
        )

        print("✅ Paper addition completed")
        print(f"   Result: {add_result[:500]}...")  # Show first 500 chars

        # Check if it succeeded
        if "❌" in add_result:
            print("❌ Test revealed issues - check the error message above")
            return False
        else:
            print("✅ Paper successfully added to Zotero!")
            return True

    except Exception as e:
        print(f"❌ **Test Failed**: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_add_to_zotero_fix())
    if success:
        print("\n🎉 **add_to_zotero function is now working correctly!**")
    else:
        print("\n❌ **Fix unsuccessful** - check error messages above")