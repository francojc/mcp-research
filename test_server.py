#!/usr/bin/env python3
"""Simple test script to verify the MCP server functionality."""

import asyncio
import logging
from arxiv_client import ArxivClient
from semantic_scholar_client import SemanticScholarClient


async def test_arxiv():
    """Test arXiv client functionality."""
    print("\n🔬 Testing arXiv API...")
    client = ArxivClient()

    try:
        # Test search
        result = await client.search("machine learning", max_results=3)
        print(f"✅ Found {len(result.papers)} papers from arXiv")

        if result.papers:
            paper = result.papers[0]
            print(f"   Title: {paper.title}")
            print(f"   Authors: {[a.name for a in paper.authors]}")
            print(f"   Published: {paper.published_date}")

        # Test get paper by ID
        if result.papers:
            paper_detail = await client.get_paper_by_id(result.papers[0].arxiv_id)
            if paper_detail:
                print(f"✅ Retrieved paper details for {paper_detail.arxiv_id}")
            else:
                print("❌ Failed to retrieve paper details")

    except Exception as e:
        print(f"❌ arXiv test failed: {e}")
    finally:
        await client.close()


async def test_semantic_scholar():
    """Test Semantic Scholar client functionality."""
    print("\n📚 Testing Semantic Scholar API...")
    client = SemanticScholarClient()

    try:
        # Test search
        result = await client.search("transformers attention", max_results=3)
        print(f"✅ Found {len(result.papers)} papers from Semantic Scholar")

        if result.papers:
            paper = result.papers[0]
            print(f"   Title: {paper.title}")
            print(f"   Authors: {[a.name for a in paper.authors]}")
            print(f"   Citations: {paper.citation_count}")

        # Test get paper details
        if result.papers:
            paper_detail = await client.get_paper_by_id(result.papers[0].source_id)
            if paper_detail:
                print(f"✅ Retrieved paper details for {paper_detail.source_id}")
            else:
                print("❌ Failed to retrieve paper details")

    except Exception as e:
        print(f"❌ Semantic Scholar test failed: {e}")
    finally:
        await client.close()


async def test_export():
    """Test export functionality."""
    print("\n📄 Testing export functionality...")
    from export_utils import export_papers
    from models import Paper, Author
    from datetime import datetime

    # Create a test paper
    test_paper = Paper(
        id="test-123",
        title="A Test Paper on Machine Learning",
        authors=[Author(name="John Doe"), Author(name="Jane Smith")],
        abstract="This is a test abstract for demonstration purposes.",
        published_date=datetime(2024, 1, 15),
        url="https://example.com/paper/123",
        doi="10.1000/test123",
        venue="Test Conference",
        source="test",
        source_id="test-123"
    )

    try:
        # Test BibTeX export
        bibtex_export = export_papers([test_paper], "bibtex")
        print("✅ BibTeX export successful")
        print(f"   Preview: {bibtex_export.content[:100]}...")

        # Test RIS export
        ris_export = export_papers([test_paper], "ris")
        print("✅ RIS export successful")

        # Test CSL-JSON export
        csl_export = export_papers([test_paper], "csl-json")
        print("✅ CSL-JSON export successful")

    except Exception as e:
        print(f"❌ Export test failed: {e}")


async def main():
    """Run all tests."""
    print("🚀 Starting MCP Research Server Tests")
    print("=" * 50)

    # Set up logging to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Run tests
    await test_arxiv()
    await test_semantic_scholar()
    await test_export()

    print("\n" + "=" * 50)
    print("✨ Test suite completed!")
    print("\n💡 If all tests passed, your MCP server should work correctly.")
    print("   Next steps:")
    print("   1. Set up Claude Desktop configuration")
    print("   2. Add your Semantic Scholar API key (optional)")
    print("   3. Restart Claude Desktop")


if __name__ == "__main__":
    asyncio.run(main())