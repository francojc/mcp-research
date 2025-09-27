"""Data models for academic papers and bibliographic information."""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class Author(BaseModel):
    """Author information."""
    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None


class Paper(BaseModel):
    """Unified paper model across different academic sources."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )

    id: str
    title: str
    authors: List[Author]
    abstract: Optional[str] = None
    published_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    categories: List[str] = Field(default_factory=list)
    source: str  # 'arxiv', 'semantic_scholar', etc.
    source_id: str  # Original ID from the source

    def __hash__(self) -> int:
        """Make Paper hashable for use in sets and as dict keys."""
        # Use source_id and source as the hash basis since they should be unique
        return hash((self.source_id, self.source))

    def __eq__(self, other) -> bool:
        """Define equality based on source_id and source."""
        if not isinstance(other, Paper):
            return False
        return self.source_id == other.source_id and self.source == other.source


class Citation(BaseModel):
    """Citation information for a paper."""
    citing_paper_id: str
    cited_paper_id: str
    context: Optional[str] = None
    intent: Optional[str] = None


class SearchResult(BaseModel):
    """Search result containing papers and metadata."""
    papers: List[Paper]
    total_count: Optional[int] = None
    query: str
    source: str
    next_token: Optional[str | int] = None


class ExportFormat(BaseModel):
    """Bibliography export format."""
    format_type: str  # 'bibtex', 'ris', 'csl-json'
    content: str