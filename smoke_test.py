#!/usr/bin/env python3
"""
Smoke test for MCP Research Server.

Tests basic connectivity and core functionality with live API calls.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_environment():
  """Verify environment variables are set."""
  print("=" * 60)
  print("TEST 1: Environment Verification")
  print("=" * 60)

  required = ["SEMANTIC_SCHOLAR_API_KEY", "ZOTERO_USER_ID", "ZOTERO_API_KEY"]
  missing = [key for key in required if not os.getenv(key)]

  if missing:
    print(f"❌ Missing environment variables: {', '.join(missing)}")
    return False

  print("✓ All required environment variables are set")
  print(f"  - Semantic Scholar API Key: {os.getenv('SEMANTIC_SCHOLAR_API_KEY')[:10]}...")
  print(f"  - Zotero User ID: {os.getenv('ZOTERO_USER_ID')}")
  print(f"  - Zotero API Key: {os.getenv('ZOTERO_API_KEY')[:10]}...")
  return True


async def test_client_initialization():
  """Test that all API clients initialize successfully."""
  print("\n" + "=" * 60)
  print("TEST 2: Client Initialization")
  print("=" * 60)

  try:
    from arxiv_client import ArxivClient
    from semantic_scholar_client import SemanticScholarClient
    from google_scholar_client import GoogleScholarClient
    from zotero_client import ZoteroClient

    arxiv = ArxivClient()
    print("✓ ArxivClient initialized")

    scholar = SemanticScholarClient()
    print("✓ SemanticScholarClient initialized")

    google = GoogleScholarClient()
    print("✓ GoogleScholarClient initialized")

    zotero = ZoteroClient()
    print("✓ ZoteroClient initialized")

    # Test Zotero connection
    if zotero.zot:
      collections = zotero.zot.collections()
      print(f"✓ Zotero connection verified ({len(collections)} collections found)")

    # Cleanup
    await arxiv.close()
    await scholar.close()
    await google.close()

    return True
  except Exception as e:
    print(f"❌ Client initialization failed: {e}")
    return False


async def test_search():
  """Test basic search functionality."""
  print("\n" + "=" * 60)
  print("TEST 3: Core Search Functionality")
  print("=" * 60)

  arxiv_success = False
  scholar_success = False

  try:
    from arxiv_client import ArxivClient

    # Test arXiv search
    arxiv = ArxivClient()
    print("Testing arXiv search for 'attention is all you need'...")
    results = await arxiv.search("attention is all you need", max_results=3)
    print(f"✓ arXiv returned {len(results.papers)} papers")
    if results.papers:
      print(f"  First result: {results.papers[0].title[:60]}...")
    arxiv_success = True
    await arxiv.close()
  except Exception as e:
    print(f"❌ arXiv search failed: {e}")

  try:
    from semantic_scholar_client import SemanticScholarClient

    # Test Semantic Scholar search
    scholar = SemanticScholarClient()
    print("\nTesting Semantic Scholar search for 'transformer'...")
    results = await scholar.search("transformer", max_results=3)
    print(f"✓ Semantic Scholar returned {len(results.papers)} papers")
    if results.papers:
      print(f"  First result: {results.papers[0].title[:60]}...")
    scholar_success = True
    await scholar.close()
  except Exception as e:
    print(f"⚠ Semantic Scholar search failed (may be rate limited): {type(e).__name__}")
    # Semantic Scholar can fail due to rate limiting, so we'll count arXiv success as partial pass

  return arxiv_success  # At least arXiv should work


async def test_zotero():
  """Test Zotero integration."""
  print("\n" + "=" * 60)
  print("TEST 4: Zotero Integration")
  print("=" * 60)

  try:
    from zotero_client import ZoteroClient

    zotero = ZoteroClient()

    if not zotero.zot:
      print("❌ Zotero client not initialized (check credentials)")
      return False

    # List collections (this is an async method)
    collections = await zotero.list_collections()
    print(f"✓ Found {len(collections)} Zotero collections")
    if collections:
      print(f"  Sample collection: {collections[0].get('name', 'Unnamed')}")

    # Test library access
    items = zotero.zot.top(limit=1)
    print(f"✓ Zotero library accessible ({len(items)} items retrieved)")

    return True
  except Exception as e:
    print(f"❌ Zotero test failed: {e}")
    import traceback
    traceback.print_exc()
    return False


async def test_cache():
  """Test cache manager."""
  print("\n" + "=" * 60)
  print("TEST 5: Cache Manager")
  print("=" * 60)

  try:
    from cache_manager import CacheManager

    cache = CacheManager()
    stats = cache.get_cache_stats()

    print(f"✓ Cache initialized successfully")
    print(f"  - Search cache: {stats['search_cache']['total']} total, {stats['search_cache']['active']} active")
    print(f"  - Paper cache: {stats['paper_cache']['total']} total, {stats['paper_cache']['active']} active")
    print(f"  - Citation cache: {stats['citation_cache']['total']} total, {stats['citation_cache']['active']} active")

    return True
  except Exception as e:
    print(f"❌ Cache test failed: {e}")
    import traceback
    traceback.print_exc()
    return False


async def main():
  """Run all smoke tests."""
  print("\n" + "█" * 60)
  print("MCP RESEARCH SERVER - SMOKE TEST")
  print("█" * 60)

  results = []

  # Run tests
  results.append(await test_environment())
  results.append(await test_client_initialization())
  results.append(await test_search())
  results.append(await test_zotero())
  results.append(await test_cache())

  # Summary
  print("\n" + "=" * 60)
  print("TEST SUMMARY")
  print("=" * 60)
  passed = sum(results)
  total = len(results)

  print(f"Passed: {passed}/{total}")

  if passed == total:
    print("\n✓ All smoke tests passed!")
    return 0
  else:
    print(f"\n❌ {total - passed} test(s) failed")
    return 1


if __name__ == "__main__":
  sys.exit(asyncio.run(main()))
