"""Advanced ranking and sorting algorithms for academic papers."""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Callable, Optional
from enum import Enum

from models import Paper


class SortCriterion(Enum):
    """Available sorting criteria for papers."""
    RELEVANCE = "relevance"
    DATE = "date"
    CITATIONS = "citations"
    COMBINED = "combined"
    IMPACT = "impact"
    RECENCY = "recency"


class PaperRanker:
    """Advanced paper ranking system with multiple scoring algorithms."""

    def __init__(self):
        self.current_year = datetime.now().year

    def calculate_citation_score(self, paper: Paper) -> float:
        """Calculate citation-based score."""
        if paper.citation_count is None or paper.citation_count <= 0:
            return 0.0

        # Log scale for citations to prevent outliers from dominating
        return math.log10(paper.citation_count + 1)

    def calculate_recency_score(self, paper: Paper) -> float:
        """Calculate recency score based on publication date."""
        if not paper.published_date:
            return 0.0

        # Calculate years since publication
        years_ago = self.current_year - paper.published_date.year

        # Exponential decay with half-life of ~3 years
        decay_factor = 0.8
        return decay_factor ** max(0, years_ago - 1)

    def calculate_completeness_score(self, paper: Paper) -> float:
        """Calculate score based on metadata completeness."""
        score = 0.0
        max_score = 0.0

        # Essential fields
        fields = [
            (paper.title, 1.0),
            (paper.authors, 0.8),
            (paper.abstract, 0.7),
            (paper.doi, 0.6),
            (paper.venue, 0.5),
            (paper.published_date, 0.4),
            (paper.url or paper.pdf_url, 0.3),
            (paper.categories, 0.2)
        ]

        for field_value, weight in fields:
            max_score += weight
            if field_value:
                if isinstance(field_value, list) and len(field_value) > 0:
                    score += weight
                elif not isinstance(field_value, list):
                    score += weight

        return score / max_score if max_score > 0 else 0.0

    def calculate_impact_score(self, paper: Paper) -> float:
        """Calculate impact score combining citations and recency."""
        citation_score = self.calculate_citation_score(paper)
        recency_score = self.calculate_recency_score(paper)

        # Weighted combination: newer papers get citation boost
        base_score = citation_score
        recency_boost = recency_score * 0.3

        return base_score + recency_boost

    def calculate_venue_prestige_score(self, paper: Paper) -> float:
        """Calculate venue prestige score (simplified version)."""
        if not paper.venue:
            return 0.0

        venue_lower = paper.venue.lower()

        # High-prestige venues (this is a simplified list)
        prestigious_venues = {
            # ML/AI
            'nature', 'science', 'cell', 'nips', 'neurips', 'icml', 'iclr',
            'aaai', 'ijcai', 'kdd', 'acl', 'emnlp', 'naacl', 'coling',
            # Computer Science
            'sigcomm', 'sigmod', 'vldb', 'osdi', 'sosp', 'nsdi', 'siggraph',
            'chi', 'uist', 'ccs', 'oakland', 'ndss', 'usenix security',
            # Journals
            'nature machine intelligence', 'nature communications',
            'proceedings of the national academy of sciences',
            'journal of machine learning research', 'jmlr'
        }

        # Conference patterns
        conference_patterns = [
            'international conference', 'proceedings', 'conference on',
            'workshop on', 'symposium on', 'transactions on'
        ]

        # Check for prestigious venues
        for venue in prestigious_venues:
            if venue in venue_lower:
                return 1.0

        # Check if it's a conference/journal
        for pattern in conference_patterns:
            if pattern in venue_lower:
                return 0.6

        # Default venue score
        return 0.3

    def calculate_relevance_score(
        self,
        paper: Paper,
        query: str,
        query_terms: Optional[List[str]] = None
    ) -> float:
        """Calculate relevance score based on query matching."""
        if not query:
            return 0.0

        if query_terms is None:
            # Simple tokenization
            query_terms = [term.lower().strip() for term in query.split()]
            query_terms = [term for term in query_terms if len(term) > 2]

        if not query_terms:
            return 0.0

        score = 0.0

        # Search in title (highest weight)
        if paper.title:
            title_lower = paper.title.lower()
            title_matches = sum(1 for term in query_terms if term in title_lower)
            score += (title_matches / len(query_terms)) * 1.0

        # Search in abstract
        if paper.abstract:
            abstract_lower = paper.abstract.lower()
            abstract_matches = sum(1 for term in query_terms if term in abstract_lower)
            score += (abstract_matches / len(query_terms)) * 0.6

        # Search in categories/fields
        if paper.categories:
            categories_text = ' '.join(paper.categories).lower()
            category_matches = sum(1 for term in query_terms if term in categories_text)
            score += (category_matches / len(query_terms)) * 0.4

        # Search in venue
        if paper.venue:
            venue_lower = paper.venue.lower()
            venue_matches = sum(1 for term in query_terms if term in venue_lower)
            score += (venue_matches / len(query_terms)) * 0.3

        # Search in authors
        if paper.authors:
            authors_text = ' '.join(author.name for author in paper.authors if author.name).lower()
            author_matches = sum(1 for term in query_terms if term in authors_text)
            score += (author_matches / len(query_terms)) * 0.2

        return min(score, 1.0)  # Cap at 1.0

    def calculate_combined_score(
        self,
        paper: Paper,
        query: str = "",
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate combined score using multiple factors."""
        if weights is None:
            weights = {
                'relevance': 0.4,
                'citations': 0.25,
                'recency': 0.15,
                'impact': 0.1,
                'completeness': 0.05,
                'venue_prestige': 0.05
            }

        scores = {
            'relevance': self.calculate_relevance_score(paper, query),
            'citations': self.calculate_citation_score(paper) / 5.0,  # Normalize
            'recency': self.calculate_recency_score(paper),
            'impact': self.calculate_impact_score(paper) / 5.0,  # Normalize
            'completeness': self.calculate_completeness_score(paper),
            'venue_prestige': self.calculate_venue_prestige_score(paper)
        }

        combined_score = sum(
            scores.get(factor, 0.0) * weight
            for factor, weight in weights.items()
        )

        return combined_score

    def sort_papers(
        self,
        papers: List[Paper],
        criterion: SortCriterion = SortCriterion.RELEVANCE,
        query: str = "",
        reverse: bool = True,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> List[Paper]:
        """Sort papers by the specified criterion."""
        if not papers:
            return papers

        # Define scoring functions
        scoring_functions = {
            SortCriterion.RELEVANCE: lambda p: self.calculate_relevance_score(p, query),
            SortCriterion.DATE: lambda p: (
                p.published_date.timestamp() if p.published_date else 0
            ),
            SortCriterion.CITATIONS: lambda p: p.citation_count or 0,
            SortCriterion.COMBINED: lambda p: self.calculate_combined_score(
                p, query, custom_weights
            ),
            SortCriterion.IMPACT: lambda p: self.calculate_impact_score(p),
            SortCriterion.RECENCY: lambda p: self.calculate_recency_score(p)
        }

        scoring_function = scoring_functions.get(criterion, scoring_functions[SortCriterion.RELEVANCE])

        # Sort papers
        sorted_papers = sorted(
            papers,
            key=scoring_function,
            reverse=reverse
        )

        return sorted_papers

    def rank_papers_with_scores(
        self,
        papers: List[Paper],
        criterion: SortCriterion = SortCriterion.COMBINED,
        query: str = "",
        custom_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """Rank papers and return with their scores for debugging."""
        if not papers:
            return []

        scoring_functions = {
            SortCriterion.RELEVANCE: lambda p: self.calculate_relevance_score(p, query),
            SortCriterion.DATE: lambda p: (
                p.published_date.timestamp() if p.published_date else 0
            ),
            SortCriterion.CITATIONS: lambda p: p.citation_count or 0,
            SortCriterion.COMBINED: lambda p: self.calculate_combined_score(
                p, query, custom_weights
            ),
            SortCriterion.IMPACT: lambda p: self.calculate_impact_score(p),
            SortCriterion.RECENCY: lambda p: self.calculate_recency_score(p)
        }

        scoring_function = scoring_functions.get(criterion, scoring_functions[SortCriterion.COMBINED])

        # Calculate scores and rank
        ranked_papers = []
        for i, paper in enumerate(papers):
            score = scoring_function(paper)
            ranked_papers.append({
                'paper': paper,
                'score': score,
                'rank': i + 1
            })

        # Sort by score
        ranked_papers.sort(key=lambda x: x['score'], reverse=True)

        # Update ranks
        for i, item in enumerate(ranked_papers):
            item['rank'] = i + 1

        return ranked_papers

    def get_top_papers(
        self,
        papers: List[Paper],
        top_k: int = 10,
        criterion: SortCriterion = SortCriterion.COMBINED,
        query: str = "",
        min_score: float = 0.0
    ) -> List[Paper]:
        """Get top-k papers above minimum score threshold."""
        sorted_papers = self.sort_papers(papers, criterion, query, reverse=True)

        # Filter by minimum score if needed
        if min_score > 0.0:
            scoring_functions = {
                SortCriterion.RELEVANCE: lambda p: self.calculate_relevance_score(p, query),
                SortCriterion.COMBINED: lambda p: self.calculate_combined_score(p, query),
                SortCriterion.IMPACT: lambda p: self.calculate_impact_score(p),
                SortCriterion.RECENCY: lambda p: self.calculate_recency_score(p)
            }

            if criterion in scoring_functions:
                scoring_function = scoring_functions[criterion]
                sorted_papers = [
                    paper for paper in sorted_papers
                    if scoring_function(paper) >= min_score
                ]

        return sorted_papers[:top_k]


# Global ranker instance
paper_ranker = PaperRanker()