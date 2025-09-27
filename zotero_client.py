"""Zotero API client for MCP Research Server integration."""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import re

from pyzotero import zotero
from models import Paper, Author
from error_handler import error_handler, handle_api_error


class ZoteroClient:
    """Zotero API client with automatic tagging and collection management."""

    def __init__(self, user_id: str = None, api_key: str = None, library_type: str = "user"):
        """Initialize Zotero client with credentials."""
        self.user_id = user_id or os.getenv("ZOTERO_USER_ID")
        self.api_key = api_key or os.getenv("ZOTERO_API_KEY")
        self.library_type = library_type
        self.logger = logging.getLogger(__name__)

        if not self.user_id or not self.api_key:
            raise ValueError(
                "Zotero credentials not found. Please set ZOTERO_USER_ID and ZOTERO_API_KEY "
                "environment variables or pass them as parameters."
            )

        # Initialize pyzotero client
        try:
            self.zot = zotero.Zotero(self.user_id, self.library_type, self.api_key)
            self.logger.info(f"Zotero client initialized for {library_type} library {user_id}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Zotero client: {e}")
            raise

        # MCP Research tagging configuration
        self.mcp_tag = "mcp-research"
        self.source_tag_prefix = "source-"
        self.category_tag_prefix = "category-"
        self.venue_tag_prefix = "venue-"

    @handle_api_error
    async def test_connection(self) -> Dict[str, Any]:
        """Test Zotero API connection and permissions."""
        try:
            # Test basic connectivity
            items = self.zot.top(limit=1)

            # Test permissions
            permissions = {
                "read": True,  # If we got here, read works
                "write": False,
                "library_access": True
            }

            # Test write permissions by attempting to get template
            try:
                template = self.zot.item_template("journalArticle")
                permissions["write"] = True
            except Exception:
                pass

            return {
                "status": "connected",
                "user_id": self.user_id,
                "library_type": self.library_type,
                "permissions": permissions,
                "total_items": len(items) if items else 0
            }

        except Exception as e:
            self.logger.error(f"Zotero connection test failed: {e}")
            raise

    @handle_api_error
    async def add_paper_to_collection(
        self,
        paper: Paper,
        collection_name: str,
        additional_tags: List[str] = None,
        create_collection: bool = True,
        auto_tag_source: bool = True
    ) -> Dict[str, Any]:
        """Add a paper to a Zotero collection with comprehensive tagging."""
        additional_tags = additional_tags or []

        try:
            # Check if paper already exists
            existing_item = await self._find_existing_paper(paper)
            if existing_item:
                self.logger.info(f"Paper {paper.title} already exists in Zotero library")
                # Update tags on existing item
                await self._apply_tags_to_item(existing_item["key"], paper, additional_tags, auto_tag_source)
                return {
                    "status": "updated",
                    "item_key": existing_item["key"],
                    "title": paper.title,
                    "action": "Added tags to existing paper"
                }

            # Find or create collection
            collection_key = None
            if collection_name:
                collection_key = await self._get_or_create_collection(collection_name, create_collection)

            # Convert paper to Zotero item
            zotero_item = self._convert_paper_to_zotero_item(paper)

            # Create the item in Zotero
            response = self.zot.create_items([zotero_item])

            if not response.get("success"):
                raise Exception(f"Failed to create item: {response}")

            item_key = list(response["success"].keys())[0]
            self.logger.info(f"Created Zotero item {item_key} for paper: {paper.title}")

            # Add to collection if specified
            if collection_key:
                self.zot.addto_collection(collection_key, item_key)
                self.logger.info(f"Added item {item_key} to collection {collection_name}")

            # Apply comprehensive tagging
            await self._apply_tags_to_item(item_key, paper, additional_tags, auto_tag_source)

            return {
                "status": "created",
                "item_key": item_key,
                "collection_key": collection_key,
                "title": paper.title,
                "zotero_url": f"https://www.zotero.org/{self.library_type}s/{self.user_id}/items/{item_key}"
            }

        except Exception as e:
            self.logger.error(f"Failed to add paper to Zotero: {e}")
            raise

    @handle_api_error
    async def create_collection(
        self,
        collection_name: str,
        parent_collection: str = None,
        description: str = None
    ) -> Dict[str, Any]:
        """Create a new Zotero collection."""
        try:
            # Handle nested collection names (e.g., "Research/Machine Learning")
            if "/" in collection_name:
                parts = collection_name.split("/")
                parent_key = None

                for part in parts:
                    # Check if this level already exists
                    existing_collections = self.zot.collections()
                    existing_key = None

                    for collection in existing_collections:
                        if (collection["data"]["name"] == part and
                            collection["data"]["parentCollection"] == (parent_key or "")):
                            existing_key = collection["key"]
                            break

                    if existing_key:
                        parent_key = existing_key
                    else:
                        # Create this level
                        collection_data = {
                            "name": part,
                            "parentCollection": parent_key or ""
                        }
                        response = self.zot.create_collections([collection_data])

                        if response.get("success"):
                            parent_key = list(response["success"].keys())[0]
                            self.logger.info(f"Created collection: {part}")
                        else:
                            raise Exception(f"Failed to create collection {part}: {response}")

                return {
                    "status": "created",
                    "collection_key": parent_key,
                    "name": collection_name,
                    "type": "nested"
                }

            else:
                # Simple collection creation
                parent_key = None
                if parent_collection:
                    parent_key = await self._find_collection_by_name(parent_collection)
                    if not parent_key:
                        raise ValueError(f"Parent collection '{parent_collection}' not found")

                collection_data = {
                    "name": collection_name,
                    "parentCollection": parent_key or ""
                }

                response = self.zot.create_collections([collection_data])

                if response.get("success"):
                    collection_key = list(response["success"].keys())[0]
                    self.logger.info(f"Created collection: {collection_name}")

                    return {
                        "status": "created",
                        "collection_key": collection_key,
                        "name": collection_name,
                        "parent": parent_collection
                    }
                else:
                    raise Exception(f"Failed to create collection: {response}")

        except Exception as e:
            self.logger.error(f"Failed to create collection {collection_name}: {e}")
            raise

    @handle_api_error
    async def list_collections(
        self,
        show_items_count: bool = False,
        search_filter: str = None,
        show_mcp_items_only: bool = False
    ) -> List[Dict[str, Any]]:
        """List Zotero collections with optional filtering."""
        try:
            collections = self.zot.collections()
            result = []

            for collection in collections:
                collection_data = {
                    "key": collection["key"],
                    "name": collection["data"]["name"],
                    "parent_collection": collection["data"].get("parentCollection", ""),
                    "items_count": 0
                }

                # Apply search filter
                if search_filter and search_filter.lower() not in collection["data"]["name"].lower():
                    continue

                # Get items count if requested
                if show_items_count or show_mcp_items_only:
                    items = self.zot.collection_items(collection["key"])

                    if show_mcp_items_only:
                        # Count only items with mcp-research tag
                        mcp_items = [
                            item for item in items
                            if any(tag.get("tag") == self.mcp_tag for tag in item["data"].get("tags", []))
                        ]
                        collection_data["items_count"] = len(mcp_items)
                        collection_data["mcp_items_count"] = len(mcp_items)
                    else:
                        collection_data["items_count"] = len(items)

                result.append(collection_data)

            # Sort by name
            result.sort(key=lambda x: x["name"])

            return result

        except Exception as e:
            self.logger.error(f"Failed to list collections: {e}")
            raise

    async def _find_existing_paper(self, paper: Paper) -> Optional[Dict[str, Any]]:
        """Find existing paper in Zotero library by DOI or arXiv ID."""
        try:
            # Search by DOI first
            if paper.doi:
                results = self.zot.items(q=paper.doi, qmode="everything")
                if results:
                    return results[0]

            # Search by arXiv ID
            if paper.arxiv_id:
                arxiv_queries = [
                    paper.arxiv_id,
                    f"arXiv:{paper.arxiv_id}",
                    paper.arxiv_id.replace("v", "")  # Try without version
                ]

                for query in arxiv_queries:
                    results = self.zot.items(q=query, qmode="everything")
                    if results:
                        return results[0]

            # Search by title (fuzzy match)
            if paper.title:
                # Use first few words of title for search
                title_words = paper.title.split()[:5]
                title_query = " ".join(title_words)
                results = self.zot.items(q=title_query, qmode="titleCreatorYear")

                # Check for close matches
                for result in results[:5]:  # Check first 5 results
                    if self._titles_similar(paper.title, result["data"].get("title", "")):
                        return result

            return None

        except Exception as e:
            self.logger.warning(f"Error searching for existing paper: {e}")
            return None

    def _titles_similar(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """Check if two titles are similar using simple word overlap."""
        if not title1 or not title2:
            return False

        # Normalize titles
        words1 = set(re.findall(r'\w+', title1.lower()))
        words2 = set(re.findall(r'\w+', title2.lower()))

        if not words1 or not words2:
            return False

        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)

        similarity = len(intersection) / len(union)
        return similarity >= threshold

    async def _get_or_create_collection(self, collection_name: str, create_if_missing: bool) -> Optional[str]:
        """Get collection key by name, optionally creating it."""
        try:
            collection_key = await self._find_collection_by_name(collection_name)

            if not collection_key and create_if_missing:
                result = await self.create_collection(collection_name)
                collection_key = result["collection_key"]

            return collection_key

        except Exception as e:
            self.logger.error(f"Failed to get/create collection {collection_name}: {e}")
            return None

    async def _find_collection_by_name(self, collection_name: str) -> Optional[str]:
        """Find collection key by name, supporting nested names."""
        try:
            collections = self.zot.collections()

            # Handle nested collection names (e.g., "Research/Machine Learning")
            if "/" in collection_name:
                parts = collection_name.split("/")
                parent_key = ""

                for part in parts:
                    found = False
                    for collection in collections:
                        if (collection["data"]["name"] == part and
                            collection["data"]["parentCollection"] == parent_key):
                            parent_key = collection["key"]
                            found = True
                            break

                    if not found:
                        return None

                return parent_key

            else:
                # Simple name search
                for collection in collections:
                    if collection["data"]["name"] == collection_name:
                        return collection["key"]

                return None

        except Exception as e:
            self.logger.error(f"Failed to find collection {collection_name}: {e}")
            return None

    def _convert_paper_to_zotero_item(self, paper: Paper) -> Dict[str, Any]:
        """Convert a Paper object to Zotero item format."""
        # Determine item type based on paper characteristics
        if paper.arxiv_id and not paper.venue:
            item_type = "preprint"
        elif paper.venue:
            # Check if it's a journal or conference
            venue_lower = paper.venue.lower()
            if any(word in venue_lower for word in ["journal", "transactions", "letters", "review"]):
                item_type = "journalArticle"
            else:
                item_type = "conferencePaper"
        else:
            item_type = "journalArticle"  # Default

        # Get template for item type
        try:
            zotero_item = self.zot.item_template(item_type)
        except Exception:
            # Fallback to journal article if item type not supported
            zotero_item = self.zot.item_template("journalArticle")

        # Fill in the data
        zotero_item["title"] = paper.title or ""
        zotero_item["abstractNote"] = paper.abstract or ""
        zotero_item["url"] = paper.url or ""
        zotero_item["DOI"] = paper.doi or ""

        # Handle publication date
        if paper.published_date:
            zotero_item["date"] = paper.published_date.strftime("%Y-%m-%d")

        # Handle venue
        if paper.venue:
            if item_type == "journalArticle":
                zotero_item["publicationTitle"] = paper.venue
            elif item_type == "conferencePaper":
                zotero_item["proceedingsTitle"] = paper.venue
            elif item_type == "preprint":
                zotero_item["repository"] = paper.venue

        # Handle arXiv ID
        if paper.arxiv_id:
            if item_type == "preprint":
                zotero_item["archiveID"] = paper.arxiv_id
            else:
                # Add to extra field for non-preprint items
                extra_parts = []
                if zotero_item.get("extra"):
                    extra_parts.append(zotero_item["extra"])
                extra_parts.append(f"arXiv:{paper.arxiv_id}")
                zotero_item["extra"] = "\n".join(extra_parts)

        # Handle authors
        if paper.authors:
            creators = []
            for author in paper.authors:
                if author.name:
                    # Split name into first and last
                    name_parts = author.name.strip().split()
                    if len(name_parts) >= 2:
                        first_name = " ".join(name_parts[:-1])
                        last_name = name_parts[-1]
                    else:
                        first_name = ""
                        last_name = name_parts[0] if name_parts else ""

                    creator = {
                        "creatorType": "author",
                        "firstName": first_name,
                        "lastName": last_name
                    }
                    creators.append(creator)

            zotero_item["creators"] = creators

        return zotero_item

    async def _apply_tags_to_item(
        self,
        item_key: str,
        paper: Paper,
        additional_tags: List[str] = None,
        auto_tag_source: bool = True
    ) -> None:
        """Apply comprehensive tagging to a Zotero item."""
        tags = [self.mcp_tag]  # Always include MCP tag
        additional_tags = additional_tags or []

        try:
            # Source-based tags
            if auto_tag_source and paper.source:
                source_tag = f"{self.source_tag_prefix}{paper.source}"
                tags.append(source_tag)

            # Category-based tags (limit to 3 most relevant)
            if paper.categories:
                for category in paper.categories[:3]:
                    # Clean category name
                    clean_category = re.sub(r'[^\w\-.]', '', category.lower())
                    if clean_category:
                        category_tag = f"{self.category_tag_prefix}{clean_category}"
                        tags.append(category_tag)

            # Venue-based tags
            if paper.venue:
                # Clean venue name and limit length
                clean_venue = re.sub(r'[^\w\s\-]', '', paper.venue.lower())
                clean_venue = re.sub(r'\s+', '-', clean_venue.strip())
                if clean_venue:
                    venue_tag = f"{self.venue_tag_prefix}{clean_venue[:20]}"
                    tags.append(venue_tag)

            # User-specified tags
            tags.extend(additional_tags)

            # Remove duplicates and empty tags
            tags = list(set(tag for tag in tags if tag.strip()))

            # Apply tags to the item
            await self._add_tags_to_item(item_key, tags)

            self.logger.info(f"Applied {len(tags)} tags to item {item_key}: {', '.join(tags)}")

        except Exception as e:
            self.logger.error(f"Failed to apply tags to item {item_key}: {e}")

    async def _add_tags_to_item(self, item_key: str, tags: List[str]) -> None:
        """Add tags to a Zotero item."""
        try:
            # Get current item data
            item = self.zot.item(item_key)
            current_tags = item["data"].get("tags", [])

            # Convert current tags to set of tag names
            current_tag_names = {tag["tag"] for tag in current_tags}

            # Add new tags
            for tag in tags:
                if tag not in current_tag_names:
                    current_tags.append({"tag": tag})

            # Update item with new tags
            item["data"]["tags"] = current_tags
            self.zot.update_item(item)

        except Exception as e:
            self.logger.error(f"Failed to add tags to item {item_key}: {e}")
            raise

    async def get_mcp_papers_stats(self) -> Dict[str, Any]:
        """Get statistics about papers added via MCP Research Server."""
        try:
            # Search for all items with mcp-research tag
            mcp_items = []
            all_items = self.zot.everything(self.zot.top())

            for item in all_items:
                tags = item["data"].get("tags", [])
                if any(tag.get("tag") == self.mcp_tag for tag in tags):
                    mcp_items.append(item)

            # Analyze the items
            stats = {
                "total_mcp_papers": len(mcp_items),
                "by_source": {},
                "by_category": {},
                "by_item_type": {},
                "recent_additions": 0
            }

            recent_cutoff = datetime.now().replace(day=1)  # This month

            for item in mcp_items:
                tags = [tag.get("tag", "") for tag in item["data"].get("tags", [])]
                item_type = item["data"].get("itemType", "unknown")
                date_added = item.get("data", {}).get("dateAdded", "")

                # Count by item type
                stats["by_item_type"][item_type] = stats["by_item_type"].get(item_type, 0) + 1

                # Count by source
                for tag in tags:
                    if tag.startswith(self.source_tag_prefix):
                        source = tag[len(self.source_tag_prefix):]
                        stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

                # Count by category
                for tag in tags:
                    if tag.startswith(self.category_tag_prefix):
                        category = tag[len(self.category_tag_prefix):]
                        stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

                # Count recent additions
                if date_added:
                    try:
                        added_date = datetime.fromisoformat(date_added.replace("Z", "+00:00"))
                        if added_date >= recent_cutoff:
                            stats["recent_additions"] += 1
                    except Exception:
                        pass

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get MCP papers stats: {e}")
            raise