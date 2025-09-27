"""Advanced deduplication and ranking algorithms for academic papers."""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

from models import Paper


@dataclass
class DeduplicationMatch:
    """Represents a potential duplicate match between papers."""
    paper1: Paper
    paper2: Paper
    similarity_score: float
    match_reasons: List[str]
    preferred_paper: Optional[Paper] = None


class PaperDeduplicator:
    """Advanced paper deduplication using multiple similarity metrics."""

    def __init__(
        self,
        title_similarity_threshold: float = 0.85,
        doi_match_weight: float = 1.0,
        arxiv_match_weight: float = 0.95,
        title_match_weight: float = 0.8,
        author_match_weight: float = 0.3,
        venue_match_weight: float = 0.2
    ):
        self.title_similarity_threshold = title_similarity_threshold
        self.doi_match_weight = doi_match_weight
        self.arxiv_match_weight = arxiv_match_weight
        self.title_match_weight = title_match_weight
        self.author_match_weight = author_match_weight
        self.venue_match_weight = venue_match_weight

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        if not title:
            return ""

        # Convert to lowercase
        normalized = title.lower()

        # Remove common punctuation and extra whitespace
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # Remove common stop words that don't affect paper identity
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were'
        }
        words = [word for word in normalized.split() if word not in stop_words]

        return ' '.join(words)

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        if not title1 or not title2:
            return 0.0

        norm1 = self._normalize_title(title1)
        norm2 = self._normalize_title(title2)

        if not norm1 or not norm2:
            return 0.0

        # Use sequence matcher for fuzzy string matching
        return SequenceMatcher(None, norm1, norm2).ratio()

    def _extract_author_surnames(self, paper: Paper) -> Set[str]:
        """Extract normalized author surnames."""
        surnames = set()
        for author in paper.authors:
            if not author.name:
                continue

            # Extract surname (last word/part)
            name_parts = author.name.strip().split()
            if name_parts:
                surname = name_parts[-1].lower()
                # Remove common suffixes
                surname = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', surname).strip()
                if surname:
                    surnames.add(surname)

        return surnames

    def _calculate_author_overlap(self, paper1: Paper, paper2: Paper) -> float:
        """Calculate author overlap between two papers."""
        surnames1 = self._extract_author_surnames(paper1)
        surnames2 = self._extract_author_surnames(paper2)

        if not surnames1 or not surnames2:
            return 0.0

        intersection = surnames1.intersection(surnames2)
        union = surnames1.union(surnames2)

        return len(intersection) / len(union) if union else 0.0

    def _calculate_venue_similarity(self, venue1: Optional[str], venue2: Optional[str]) -> float:
        """Calculate venue similarity."""
        if not venue1 or not venue2:
            return 0.0

        # Normalize venue names
        v1 = re.sub(r'[^\w\s]', ' ', venue1.lower()).strip()
        v2 = re.sub(r'[^\w\s]', ' ', venue2.lower()).strip()

        if v1 == v2:
            return 1.0

        # Check for acronym matches (e.g., "ICML" vs "International Conference on Machine Learning")
        v1_words = set(v1.split())
        v2_words = set(v2.split())

        # Simple acronym check
        if len(v1) <= 10 and len(v2) > 20:  # v1 might be acronym of v2
            acronym = ''.join(word[0] for word in v2.split() if word)
            if v1.replace(' ', '').lower() == acronym.lower():
                return 0.8

        if len(v2) <= 10 and len(v1) > 20:  # v2 might be acronym of v1
            acronym = ''.join(word[0] for word in v1.split() if word)
            if v2.replace(' ', '').lower() == acronym.lower():
                return 0.8

        # Word overlap
        if v1_words and v2_words:
            overlap = len(v1_words.intersection(v2_words)) / len(v1_words.union(v2_words))
            return overlap

        return 0.0

    def calculate_similarity(self, paper1: Paper, paper2: Paper) -> DeduplicationMatch:
        """Calculate overall similarity between two papers."""
        if paper1.id == paper2.id:
            return DeduplicationMatch(
                paper1=paper1,
                paper2=paper2,
                similarity_score=1.0,
                match_reasons=["Same paper ID"],
                preferred_paper=paper1
            )

        total_score = 0.0
        match_reasons = []

        # DOI match (strongest indicator)
        if paper1.doi and paper2.doi and paper1.doi == paper2.doi:
            total_score = self.doi_match_weight
            match_reasons.append(f"DOI match: {paper1.doi}")

        # arXiv ID match
        elif paper1.arxiv_id and paper2.arxiv_id and paper1.arxiv_id == paper2.arxiv_id:
            total_score = self.arxiv_match_weight
            match_reasons.append(f"arXiv ID match: {paper1.arxiv_id}")

        else:
            # Calculate component similarities
            title_sim = self._calculate_title_similarity(paper1.title, paper2.title)
            author_overlap = self._calculate_author_overlap(paper1, paper2)
            venue_sim = self._calculate_venue_similarity(paper1.venue, paper2.venue)

            # Weighted combination
            total_score = (
                title_sim * self.title_match_weight +
                author_overlap * self.author_match_weight +
                venue_sim * self.venue_match_weight
            )

            if title_sim > self.title_similarity_threshold:
                match_reasons.append(f"Title similarity: {title_sim:.2f}")
            if author_overlap > 0.5:
                match_reasons.append(f"Author overlap: {author_overlap:.2f}")
            if venue_sim > 0.7:
                match_reasons.append(f"Venue similarity: {venue_sim:.2f}")

        # Determine preferred paper
        preferred_paper = self._select_preferred_paper(paper1, paper2)

        return DeduplicationMatch(
            paper1=paper1,
            paper2=paper2,
            similarity_score=total_score,
            match_reasons=match_reasons,
            preferred_paper=preferred_paper
        )

    def _select_preferred_paper(self, paper1: Paper, paper2: Paper) -> Paper:
        """Select the preferred paper from a duplicate pair."""
        # Prefer paper with DOI
        if paper1.doi and not paper2.doi:
            return paper1
        if paper2.doi and not paper1.doi:
            return paper2

        # Prefer paper with more complete metadata
        score1 = self._calculate_completeness_score(paper1)
        score2 = self._calculate_completeness_score(paper2)

        if score1 > score2:
            return paper1
        elif score2 > score1:
            return paper2

        # Prefer more recent publication
        if paper1.published_date and paper2.published_date:
            from datetime import timezone
            # Ensure both dates are timezone-aware for comparison
            date1 = paper1.published_date
            date2 = paper2.published_date
            if date1.tzinfo is None:
                date1 = date1.replace(tzinfo=timezone.utc)
            if date2.tzinfo is None:
                date2 = date2.replace(tzinfo=timezone.utc)
            return paper1 if date1 >= date2 else paper2

        # Default to first paper
        return paper1

    def _calculate_completeness_score(self, paper: Paper) -> float:
        """Calculate how complete a paper's metadata is."""
        score = 0.0
        max_score = 0.0

        # Title (required)
        max_score += 1.0
        if paper.title:
            score += 1.0

        # Authors
        max_score += 1.0
        if paper.authors:
            score += 1.0

        # Abstract
        max_score += 0.8
        if paper.abstract:
            score += 0.8

        # DOI
        max_score += 0.6
        if paper.doi:
            score += 0.6

        # Venue
        max_score += 0.5
        if paper.venue:
            score += 0.5

        # Publication date
        max_score += 0.4
        if paper.published_date:
            score += 0.4

        # Citation count
        max_score += 0.3
        if paper.citation_count is not None:
            score += 0.3

        # Categories/fields
        max_score += 0.2
        if paper.categories:
            score += 0.2

        return score / max_score if max_score > 0 else 0.0

    def deduplicate_papers(
        self,
        papers: List[Paper],
        similarity_threshold: float = 0.8
    ) -> Tuple[List[Paper], List[DeduplicationMatch]]:
        """
        Deduplicate a list of papers.

        Returns:
            Tuple of (deduplicated_papers, duplicate_matches)
        """
        if len(papers) <= 1:
            return papers, []

        # Find all potential duplicates
        duplicates = []
        processed_pairs = set()

        for i, paper1 in enumerate(papers):
            for j, paper2 in enumerate(papers[i + 1:], i + 1):
                pair_key = tuple(sorted([paper1.id, paper2.id]))
                if pair_key in processed_pairs:
                    continue

                processed_pairs.add(pair_key)
                match = self.calculate_similarity(paper1, paper2)

                if match.similarity_score >= similarity_threshold:
                    duplicates.append(match)

        # Build groups of duplicate papers
        duplicate_groups = []
        paper_to_group = {}

        for match in duplicates:
            group1 = paper_to_group.get(match.paper1.id)
            group2 = paper_to_group.get(match.paper2.id)

            if group1 is None and group2 is None:
                # Create new group
                new_group = {match.paper1, match.paper2}
                duplicate_groups.append(new_group)
                paper_to_group[match.paper1.id] = new_group
                paper_to_group[match.paper2.id] = new_group

            elif group1 is not None and group2 is None:
                # Add paper2 to group1
                group1.add(match.paper2)
                paper_to_group[match.paper2.id] = group1

            elif group1 is None and group2 is not None:
                # Add paper1 to group2
                group2.add(match.paper1)
                paper_to_group[match.paper1.id] = group2

            elif group1 is not group2:
                # Merge groups
                merged_group = group1.union(group2)
                duplicate_groups.remove(group1)
                duplicate_groups.remove(group2)
                duplicate_groups.append(merged_group)

                # Update mappings
                for paper in merged_group:
                    paper_to_group[paper.id] = merged_group

        # Select best representative from each group
        deduplicated = []
        processed_paper_ids = set()

        for paper in papers:
            if paper.id in processed_paper_ids:
                continue

            group = paper_to_group.get(paper.id)
            if group:
                # Select best paper from group
                best_paper = max(group, key=self._calculate_completeness_score)
                deduplicated.append(best_paper)
                processed_paper_ids.update(p.id for p in group)
            else:
                # No duplicates found
                deduplicated.append(paper)
                processed_paper_ids.add(paper.id)

        return deduplicated, duplicates


# Global deduplicator instance
paper_deduplicator = PaperDeduplicator()