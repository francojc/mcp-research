"""Advanced search functionality with field-specific queries and Boolean operators."""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum

from models import Paper, SearchResult


class SearchField(Enum):
    """Supported search fields."""
    ANY = "any"
    TITLE = "title"
    AUTHOR = "author"
    ABSTRACT = "abstract"
    VENUE = "venue"
    CATEGORY = "category"
    DOI = "doi"
    ARXIV_ID = "arxiv_id"


class BooleanOperator(Enum):
    """Boolean search operators."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


@dataclass
class SearchTerm:
    """Represents a search term with field and operator information."""
    text: str
    field: SearchField = SearchField.ANY
    operator: Optional[BooleanOperator] = None
    exact_match: bool = False
    proximity: Optional[int] = None  # For phrase proximity searches


@dataclass
class DateRange:
    """Date range for publication filtering."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None


@dataclass
class AdvancedSearchQuery:
    """Advanced search query with multiple criteria."""
    terms: List[SearchTerm]
    date_range: Optional[DateRange] = None
    min_citations: Optional[int] = None
    sources: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    venues: Optional[List[str]] = None
    authors: Optional[List[str]] = None


class QueryBuilder:
    """Build complex search queries from natural language or structured input."""

    def __init__(self):
        self.boolean_operators = ["AND", "OR", "NOT"]
        self.field_prefixes = {
            "title:": SearchField.TITLE,
            "author:": SearchField.AUTHOR,
            "abstract:": SearchField.ABSTRACT,
            "venue:": SearchField.VENUE,
            "category:": SearchField.CATEGORY,
            "doi:": SearchField.DOI,
            "arxiv:": SearchField.ARXIV_ID,
            "intitle:": SearchField.TITLE,  # Google Scholar style
            "inauthor:": SearchField.AUTHOR,  # Google Scholar style
            "source:": SearchField.VENUE,  # Google Scholar style
        }

    def parse_query_string(self, query: str) -> AdvancedSearchQuery:
        """Parse a query string into structured search terms."""
        terms = []
        remaining_text = query

        # Extract quoted phrases first
        quoted_phrases = re.findall(r'"([^"]+)"', remaining_text)
        for phrase in quoted_phrases:
            terms.append(SearchTerm(text=phrase, exact_match=True))
            remaining_text = remaining_text.replace(f'"{phrase}"', "")

        # Extract field-specific searches
        for prefix, field in self.field_prefixes.items():
            pattern = rf'{re.escape(prefix)}(\S+(?:\s+\S+)*?)(?:\s+(?:AND|OR|NOT)|\s*$)'
            matches = re.findall(pattern, remaining_text, re.IGNORECASE)
            for match in matches:
                terms.append(SearchTerm(text=match.strip(), field=field))
                remaining_text = re.sub(
                    rf'{re.escape(prefix)}{re.escape(match.strip())}',
                    "",
                    remaining_text,
                    flags=re.IGNORECASE
                )

        # Extract Boolean operators and remaining terms
        tokens = remaining_text.split()
        current_term = []
        current_operator = None

        for token in tokens:
            if token.upper() in self.boolean_operators:
                if current_term:
                    term_text = " ".join(current_term).strip()
                    if term_text:
                        terms.append(SearchTerm(text=term_text, operator=current_operator))
                    current_term = []

                if token.upper() == "NOT":
                    current_operator = BooleanOperator.NOT
                else:
                    current_operator = BooleanOperator.AND if token.upper() == "AND" else BooleanOperator.OR
            else:
                current_term.append(token)

        # Add final term
        if current_term:
            term_text = " ".join(current_term).strip()
            if term_text:
                terms.append(SearchTerm(text=term_text, operator=current_operator))

        return AdvancedSearchQuery(terms=terms)

    def build_arxiv_query(self, search_query: AdvancedSearchQuery) -> str:
        """Build arXiv-specific query string."""
        query_parts = []

        for term in search_query.terms:
            if term.operator == BooleanOperator.NOT:
                continue  # arXiv doesn't support NOT operator directly

            prefix = ""
            if term.field == SearchField.TITLE:
                prefix = "ti:"
            elif term.field == SearchField.AUTHOR:
                prefix = "au:"
            elif term.field == SearchField.ABSTRACT:
                prefix = "abs:"
            elif term.field == SearchField.CATEGORY:
                prefix = "cat:"

            if term.exact_match:
                query_parts.append(f'{prefix}"{term.text}"')
            else:
                query_parts.append(f"{prefix}{term.text}")

        # Join with AND (arXiv default)
        return " AND ".join(query_parts) if query_parts else ""

    def build_semantic_scholar_query(self, search_query: AdvancedSearchQuery) -> str:
        """Build Semantic Scholar query string."""
        query_parts = []

        for term in search_query.terms:
            if term.operator == BooleanOperator.NOT:
                continue  # Semantic Scholar has limited NOT support

            # Semantic Scholar uses simple keyword search
            # Field-specific searches are limited
            if term.field == SearchField.AUTHOR:
                query_parts.append(f"author:{term.text}")
            elif term.exact_match:
                query_parts.append(f'"{term.text}"')
            else:
                query_parts.append(term.text)

        return " ".join(query_parts) if query_parts else ""

    def build_google_scholar_query(self, search_query: AdvancedSearchQuery) -> str:
        """Build Google Scholar query string."""
        query_parts = []

        for term in search_query.terms:
            prefix = ""
            if term.field == SearchField.TITLE:
                prefix = "intitle:"
            elif term.field == SearchField.AUTHOR:
                prefix = "author:"
            elif term.field == SearchField.VENUE:
                prefix = "source:"

            if term.operator == BooleanOperator.NOT:
                if term.exact_match:
                    query_parts.append(f'-"{prefix}{term.text}"')
                else:
                    query_parts.append(f"-{prefix}{term.text}")
            elif term.exact_match:
                query_parts.append(f'{prefix}"{term.text}"')
            else:
                query_parts.append(f"{prefix}{term.text}")

        return " ".join(query_parts) if query_parts else ""

    def create_field_specific_query(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        abstract: Optional[str] = None,
        venue: Optional[str] = None,
        keywords: Optional[str] = None,
        exact_phrase: Optional[str] = None,
        any_words: Optional[str] = None,
        without_words: Optional[str] = None,
        date_range: Optional[DateRange] = None
    ) -> AdvancedSearchQuery:
        """Create structured query from field-specific parameters."""
        terms = []

        if title:
            terms.append(SearchTerm(text=title, field=SearchField.TITLE))

        if author:
            terms.append(SearchTerm(text=author, field=SearchField.AUTHOR))

        if abstract:
            terms.append(SearchTerm(text=abstract, field=SearchField.ABSTRACT))

        if venue:
            terms.append(SearchTerm(text=venue, field=SearchField.VENUE))

        if keywords:
            terms.append(SearchTerm(text=keywords, field=SearchField.ANY))

        if exact_phrase:
            terms.append(SearchTerm(text=exact_phrase, exact_match=True))

        if any_words:
            # Split and create OR terms
            words = any_words.split()
            for i, word in enumerate(words):
                operator = BooleanOperator.OR if i > 0 else None
                terms.append(SearchTerm(text=word, operator=operator))

        if without_words:
            # Create NOT terms
            words = without_words.split()
            for word in words:
                terms.append(SearchTerm(text=word, operator=BooleanOperator.NOT))

        return AdvancedSearchQuery(terms=terms, date_range=date_range)

    def create_boolean_query(
        self,
        must_include: Optional[List[str]] = None,
        should_include: Optional[List[str]] = None,
        must_not_include: Optional[List[str]] = None
    ) -> AdvancedSearchQuery:
        """Create Boolean query with must/should/must_not logic."""
        terms = []

        if must_include:
            for term in must_include:
                terms.append(SearchTerm(text=term, operator=BooleanOperator.AND))

        if should_include:
            for term in should_include:
                terms.append(SearchTerm(text=term, operator=BooleanOperator.OR))

        if must_not_include:
            for term in must_not_include:
                terms.append(SearchTerm(text=term, operator=BooleanOperator.NOT))

        return AdvancedSearchQuery(terms=terms)

    def suggest_query_improvements(self, query: str) -> List[str]:
        """Suggest improvements for better search results."""
        suggestions = []

        # Check for common issues
        if not re.search(r'[":()]', query):
            suggestions.append("Consider using quotes for exact phrases: \"machine learning\"")

        if "and" in query.lower() and "AND" not in query:
            suggestions.append("Use uppercase AND for boolean search: machine learning AND neural networks")

        if "or" in query.lower() and "OR" not in query:
            suggestions.append("Use uppercase OR for alternative terms: transformer OR attention")

        if len(query.split()) > 10:
            suggestions.append("Try shorter, more focused queries for better results")

        # Check for field-specific suggestions
        if "author" in query.lower() and "author:" not in query:
            suggestions.append("Use author: prefix to search by author: author:\"John Smith\"")

        if "title" in query.lower() and "title:" not in query:
            suggestions.append("Use title: prefix to search in titles: title:\"attention is all you need\"")

        if not suggestions:
            suggestions.append("Try using boolean operators (AND, OR, NOT) for more precise searches")
            suggestions.append("Use quotes for exact phrases: \"natural language processing\"")
            suggestions.append("Use field prefixes: author:Smith title:transformer")

        return suggestions


class AdvancedSearchEngine:
    """Execute advanced searches across multiple sources."""

    def __init__(self, arxiv_client, semantic_scholar_client, google_scholar_client=None):
        self.arxiv_client = arxiv_client
        self.semantic_scholar_client = semantic_scholar_client
        self.google_scholar_client = google_scholar_client
        self.query_builder = QueryBuilder()

    async def search(
        self,
        query: Union[str, AdvancedSearchQuery],
        sources: List[str] = None,
        max_results: int = 20,
        date_range: Optional[DateRange] = None
    ) -> Dict[str, SearchResult]:
        """Execute advanced search across specified sources."""
        if sources is None:
            sources = ["arxiv", "semantic_scholar"]
            if self.google_scholar_client:
                sources.append("google_scholar")

        # Parse query if it's a string
        if isinstance(query, str):
            search_query = self.query_builder.parse_query_string(query)
        else:
            search_query = query

        # Apply date range if provided
        if date_range:
            search_query.date_range = date_range

        results = {}

        # Search each source
        for source in sources:
            try:
                if source == "arxiv" and self.arxiv_client:
                    arxiv_query = self.query_builder.build_arxiv_query(search_query)
                    if arxiv_query:
                        result = await self.arxiv_client.search(
                            arxiv_query,
                            max_results=max_results
                        )
                        results[source] = result

                elif source == "semantic_scholar" and self.semantic_scholar_client:
                    ss_query = self.query_builder.build_semantic_scholar_query(search_query)
                    if ss_query:
                        result = await self.semantic_scholar_client.search(
                            ss_query,
                            max_results=max_results
                        )
                        results[source] = result

                elif source == "google_scholar" and self.google_scholar_client:
                    gs_query = self.query_builder.build_google_scholar_query(search_query)
                    if gs_query:
                        # Add date filtering for Google Scholar
                        year_low = None
                        year_high = None
                        if search_query.date_range:
                            if search_query.date_range.start:
                                year_low = search_query.date_range.start.year
                            if search_query.date_range.end:
                                year_high = search_query.date_range.end.year

                        result = await self.google_scholar_client.search(
                            gs_query,
                            max_results=max_results,
                            year_low=year_low,
                            year_high=year_high
                        )
                        results[source] = result

            except Exception as e:
                # Log error but continue with other sources
                import logging
                logging.getLogger(__name__).error(f"Search failed for {source}: {e}")
                results[source] = SearchResult(
                    papers=[],
                    total_count=0,
                    query=str(query),
                    source=source
                )

        return results

    async def search_by_fields(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        abstract: Optional[str] = None,
        venue: Optional[str] = None,
        keywords: Optional[str] = None,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        sources: Optional[List[str]] = None,
        max_results: int = 20
    ) -> Dict[str, SearchResult]:
        """Search by specific fields across sources."""
        date_range = None
        if year_start or year_end:
            date_range = DateRange(
                start=datetime(year_start, 1, 1) if year_start else None,
                end=datetime(year_end, 12, 31) if year_end else None
            )

        search_query = self.query_builder.create_field_specific_query(
            title=title,
            author=author,
            abstract=abstract,
            venue=venue,
            keywords=keywords,
            date_range=date_range
        )

        return await self.search(search_query, sources, max_results, date_range)

    def suggest_query_improvements(self, query: str) -> List[str]:
        """Suggest improvements for better search results."""
        suggestions = []

        # Check for common issues
        if not re.search(r'[":()]', query):
            suggestions.append("Consider using quotes for exact phrases: \"machine learning\"")

        if "and" in query.lower() and "AND" not in query:
            suggestions.append("Use uppercase AND for Boolean operations: machine learning AND neural networks")

        if len(query.split()) == 1:
            suggestions.append("Try adding more specific terms or use field prefixes like title: or author:")

        # Suggest field-specific searches
        if not any(prefix in query.lower() for prefix in ["title:", "author:", "abstract:"]):
            suggestions.append("Use field prefixes for targeted search: title:\"your topic\" author:\"researcher name\"")

        return suggestions


# Global query builder instance
query_builder = QueryBuilder()