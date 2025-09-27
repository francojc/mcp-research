"""Paper recommendation system based on citations, content similarity, and user preferences."""

import math
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass

from models import Paper
from deduplication import PaperDeduplicator
from ranking import PaperRanker


@dataclass
class RecommendationScore:
    """Score breakdown for a recommended paper."""
    paper: Paper
    total_score: float
    citation_score: float = 0.0
    content_score: float = 0.0
    collaboration_score: float = 0.0
    recency_score: float = 0.0
    venue_score: float = 0.0


class PaperRecommendationSystem:
    """Advanced recommendation system for academic papers."""

    def __init__(self):
        self.deduplicator = PaperDeduplicator()
        self.ranker = PaperRanker()

    def extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text."""
        if not text:
            return set()

        # Simple keyword extraction (could be enhanced with NLP libraries)
        import re

        # Convert to lowercase and split
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())

        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
            'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy',
            'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'this', 'that',
            'with', 'have', 'from', 'they', 'know', 'want', 'been', 'good', 'much',
            'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long',
            'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were',
            'what', 'year', 'your', 'work', 'about', 'after', 'again', 'before',
            'other', 'right', 'think', 'where', 'being', 'every', 'great', 'might',
            'shall', 'still', 'those', 'under', 'while', 'never', 'should', 'through'
        }

        # Filter out stop words and short words
        keywords = {word for word in words if word not in stop_words and len(word) > 3}

        # Return most meaningful keywords (could use TF-IDF here)
        return keywords

    def calculate_content_similarity(self, paper1: Paper, paper2: Paper) -> float:
        """Calculate content similarity between two papers."""
        # Extract text content from papers
        text1 = " ".join(filter(None, [
            paper1.title or "",
            paper1.abstract or "",
            " ".join(paper1.categories) if paper1.categories else ""
        ]))

        text2 = " ".join(filter(None, [
            paper2.title or "",
            paper2.abstract or "",
            " ".join(paper2.categories) if paper2.categories else ""
        ]))

        if not text1 or not text2:
            return 0.0

        # Extract keywords
        keywords1 = self.extract_keywords(text1)
        keywords2 = self.extract_keywords(text2)

        if not keywords1 or not keywords2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)

        return len(intersection) / len(union) if union else 0.0

    def calculate_author_collaboration_score(self, target_paper: Paper, candidate_paper: Paper) -> float:
        """Calculate collaboration score based on shared authors."""
        if not target_paper.authors or not candidate_paper.authors:
            return 0.0

        target_surnames = {author.name.split()[-1].lower() for author in target_paper.authors if author.name}
        candidate_surnames = {author.name.split()[-1].lower() for author in candidate_paper.authors if author.name}

        if not target_surnames or not candidate_surnames:
            return 0.0

        # Direct collaboration (shared authors)
        shared_authors = target_surnames.intersection(candidate_surnames)
        if shared_authors:
            return 1.0  # Maximum score for direct collaboration

        return 0.0

    def find_citation_based_recommendations(
        self,
        target_papers: List[Paper],
        candidate_papers: List[Paper],
        max_recommendations: int = 10
    ) -> List[RecommendationScore]:
        """Find recommendations based on citation patterns."""
        recommendations = []
        target_paper_ids = {paper.id for paper in target_papers}

        for candidate in candidate_papers:
            if candidate.id in target_paper_ids:
                continue  # Skip papers already in target set

            citation_score = 0.0

            # Score based on citation count (normalized)
            if candidate.citation_count:
                # Log scale to prevent extremely cited papers from dominating
                citation_score = math.log10(candidate.citation_count + 1) / 5.0

            rec_score = RecommendationScore(
                paper=candidate,
                total_score=citation_score,
                citation_score=citation_score
            )
            recommendations.append(rec_score)

        # Sort by citation score and return top results
        recommendations.sort(key=lambda x: x.citation_score, reverse=True)
        return recommendations[:max_recommendations]

    def find_content_based_recommendations(
        self,
        target_papers: List[Paper],
        candidate_papers: List[Paper],
        max_recommendations: int = 10,
        min_similarity: float = 0.1
    ) -> List[RecommendationScore]:
        """Find recommendations based on content similarity."""
        recommendations = []
        target_paper_ids = {paper.id for paper in target_papers}

        for candidate in candidate_papers:
            if candidate.id in target_paper_ids:
                continue

            # Calculate average content similarity with target papers
            similarities = []
            for target in target_papers:
                sim = self.calculate_content_similarity(target, candidate)
                similarities.append(sim)

            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

            if avg_similarity >= min_similarity:
                rec_score = RecommendationScore(
                    paper=candidate,
                    total_score=avg_similarity,
                    content_score=avg_similarity
                )
                recommendations.append(rec_score)

        # Sort by content similarity and return top results
        recommendations.sort(key=lambda x: x.content_score, reverse=True)
        return recommendations[:max_recommendations]

    def find_hybrid_recommendations(
        self,
        target_papers: List[Paper],
        candidate_papers: List[Paper],
        max_recommendations: int = 10,
        weights: Optional[Dict[str, float]] = None
    ) -> List[RecommendationScore]:
        """Find recommendations using hybrid approach combining multiple signals."""
        if weights is None:
            weights = {
                'content': 0.4,
                'citations': 0.3,
                'collaboration': 0.1,
                'recency': 0.1,
                'venue': 0.1
            }

        recommendations = []
        target_paper_ids = {paper.id for paper in target_papers}

        # Extract target paper characteristics
        target_venues = {paper.venue.lower() for paper in target_papers if paper.venue}
        target_categories = set()
        for paper in target_papers:
            if paper.categories:
                target_categories.update(cat.lower() for cat in paper.categories)

        for candidate in candidate_papers:
            if candidate.id in target_paper_ids:
                continue

            # Calculate individual scores
            content_score = 0.0
            if target_papers:
                similarities = [
                    self.calculate_content_similarity(target, candidate)
                    for target in target_papers
                ]
                content_score = max(similarities) if similarities else 0.0

            # Citation score (normalized)
            citation_score = 0.0
            if candidate.citation_count:
                citation_score = min(math.log10(candidate.citation_count + 1) / 5.0, 1.0)

            # Collaboration score
            collaboration_score = 0.0
            for target in target_papers:
                collab_score = self.calculate_author_collaboration_score(target, candidate)
                collaboration_score = max(collaboration_score, collab_score)

            # Recency score
            recency_score = self.ranker.calculate_recency_score(candidate)

            # Venue similarity score
            venue_score = 0.0
            if candidate.venue and target_venues:
                candidate_venue = candidate.venue.lower()
                venue_score = 1.0 if candidate_venue in target_venues else 0.0

            # Category similarity score
            category_score = 0.0
            if candidate.categories and target_categories:
                candidate_categories = {cat.lower() for cat in candidate.categories}
                intersection = candidate_categories.intersection(target_categories)
                union = candidate_categories.union(target_categories)
                category_score = len(intersection) / len(union) if union else 0.0

            # Combine venue and category scores
            venue_final = max(venue_score, category_score)

            # Calculate weighted total score
            total_score = (
                content_score * weights['content'] +
                citation_score * weights['citations'] +
                collaboration_score * weights['collaboration'] +
                recency_score * weights['recency'] +
                venue_final * weights['venue']
            )

            rec_score = RecommendationScore(
                paper=candidate,
                total_score=total_score,
                content_score=content_score,
                citation_score=citation_score,
                collaboration_score=collaboration_score,
                recency_score=recency_score,
                venue_score=venue_final
            )

            recommendations.append(rec_score)

        # Sort by total score and return top results
        recommendations.sort(key=lambda x: x.total_score, reverse=True)
        return recommendations[:max_recommendations]

    def recommend_similar_papers(
        self,
        seed_papers: List[Paper],
        candidate_pool: List[Paper],
        method: str = "hybrid",
        max_recommendations: int = 10,
        **kwargs
    ) -> List[RecommendationScore]:
        """
        Recommend papers similar to the seed papers.

        Args:
            seed_papers: Papers to base recommendations on
            candidate_pool: Pool of candidate papers to recommend from
            method: Recommendation method ('content', 'citations', 'hybrid')
            max_recommendations: Maximum number of recommendations
            **kwargs: Additional parameters for specific methods
        """
        if not seed_papers or not candidate_pool:
            return []

        # Remove duplicates from candidate pool
        unique_candidates, _ = self.deduplicator.deduplicate_papers(candidate_pool)

        if method == "content":
            return self.find_content_based_recommendations(
                seed_papers,
                unique_candidates,
                max_recommendations,
                kwargs.get('min_similarity', 0.1)
            )
        elif method == "citations":
            return self.find_citation_based_recommendations(
                seed_papers,
                unique_candidates,
                max_recommendations
            )
        elif method == "hybrid":
            return self.find_hybrid_recommendations(
                seed_papers,
                unique_candidates,
                max_recommendations,
                kwargs.get('weights')
            )
        else:
            raise ValueError(f"Unknown recommendation method: {method}")

    def get_trending_papers(
        self,
        papers: List[Paper],
        time_window_days: int = 365,
        min_citations: int = 10
    ) -> List[Paper]:
        """Get papers that are trending (high recent citation velocity)."""
        from datetime import datetime, timedelta, timezone

        # Use timezone-aware datetime to avoid comparison issues
        now_utc = datetime.now(timezone.utc)
        cutoff_date = now_utc - timedelta(days=time_window_days)

        trending_papers = []
        for paper in papers:
            if (paper.citation_count and paper.citation_count >= min_citations and
                    paper.published_date):

                # Ensure paper.published_date is timezone-aware
                pub_date = paper.published_date
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)

                if pub_date >= cutoff_date:
                    # Calculate citation velocity (citations per day since publication)
                    days_since_pub = (now_utc - pub_date).days
                if days_since_pub > 0:
                    citation_velocity = paper.citation_count / days_since_pub
                    if citation_velocity > 0.1:  # Arbitrary threshold
                        trending_papers.append(paper)

        # Sort by citation velocity
        trending_papers.sort(
            key=lambda p: (p.citation_count / max(1, (datetime.now() - p.published_date).days)),
            reverse=True
        )

        return trending_papers

    def recommend_by_research_interests(
        self,
        interests: List[str],
        candidate_papers: List[Paper],
        max_recommendations: int = 10
    ) -> List[RecommendationScore]:
        """Recommend papers based on research interests/keywords."""
        interest_keywords = set()
        for interest in interests:
            interest_keywords.update(self.extract_keywords(interest.lower()))

        recommendations = []

        for paper in candidate_papers:
            # Extract paper keywords
            paper_text = " ".join(filter(None, [
                paper.title or "",
                paper.abstract or "",
                " ".join(paper.categories) if paper.categories else ""
            ]))

            paper_keywords = self.extract_keywords(paper_text)

            if interest_keywords and paper_keywords:
                # Calculate keyword overlap
                intersection = interest_keywords.intersection(paper_keywords)
                union = interest_keywords.union(paper_keywords)
                content_score = len(intersection) / len(union) if union else 0.0

                if content_score > 0:
                    # Boost score with other factors
                    citation_boost = 0.0
                    if paper.citation_count:
                        citation_boost = min(math.log10(paper.citation_count + 1) / 10.0, 0.3)

                    recency_boost = self.ranker.calculate_recency_score(paper) * 0.2

                    total_score = content_score + citation_boost + recency_boost

                    rec_score = RecommendationScore(
                        paper=paper,
                        total_score=total_score,
                        content_score=content_score,
                        citation_score=citation_boost,
                        recency_score=recency_boost
                    )
                    recommendations.append(rec_score)

        # Sort and return top recommendations
        recommendations.sort(key=lambda x: x.total_score, reverse=True)
        return recommendations[:max_recommendations]


# Global recommendation system instance
recommendation_system = PaperRecommendationSystem()