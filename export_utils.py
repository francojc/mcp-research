"""Utilities for exporting bibliographic data in various formats."""

import json
from typing import List
from models import Paper, ExportFormat


def paper_to_bibtex(paper: Paper) -> str:
    """Convert a paper to BibTeX format."""
    # Determine entry type
    entry_type = "article"
    if paper.arxiv_id:
        entry_type = "misc"

    # Create citation key
    first_author = paper.authors[0].name.split()[-1] if paper.authors else "unknown"
    year = paper.published_date.year if paper.published_date else "unknown"
    title_words = paper.title.split()[:2] if paper.title else ["unknown"]
    key = f"{first_author}{year}{''.join(title_words)}"

    bibtex = f"@{entry_type}{{{key},\n"

    if paper.title:
        bibtex += f"  title = {{{paper.title}}},\n"

    if paper.authors:
        authors = " and ".join([author.name for author in paper.authors])
        bibtex += f"  author = {{{authors}}},\n"

    if paper.published_date:
        bibtex += f"  year = {{{paper.published_date.year}}},\n"

    if paper.venue:
        if entry_type == "article":
            bibtex += f"  journal = {{{paper.venue}}},\n"
        else:
            bibtex += f"  booktitle = {{{paper.venue}}},\n"

    if paper.doi:
        bibtex += f"  doi = {{{paper.doi}}},\n"

    if paper.url:
        bibtex += f"  url = {{{paper.url}}},\n"

    if paper.abstract:
        bibtex += f"  abstract = {{{paper.abstract}}},\n"

    if paper.arxiv_id:
        bibtex += f"  eprint = {{{paper.arxiv_id}}},\n"
        bibtex += f"  archivePrefix = {{arXiv}},\n"

    bibtex += "}\n"
    return bibtex


def paper_to_ris(paper: Paper) -> str:
    """Convert a paper to RIS format."""
    ris_lines = []

    # Type
    if paper.arxiv_id:
        ris_lines.append("TY  - RPRT")  # Report
    else:
        ris_lines.append("TY  - JOUR")  # Journal article

    if paper.title:
        ris_lines.append(f"TI  - {paper.title}")

    for author in paper.authors:
        ris_lines.append(f"AU  - {author.name}")

    if paper.published_date:
        ris_lines.append(f"PY  - {paper.published_date.year}")
        if paper.published_date.month:
            ris_lines.append(f"DA  - {paper.published_date.strftime('%Y/%m/%d')}")

    if paper.venue:
        ris_lines.append(f"JO  - {paper.venue}")

    if paper.abstract:
        ris_lines.append(f"AB  - {paper.abstract}")

    if paper.doi:
        ris_lines.append(f"DO  - {paper.doi}")

    if paper.url:
        ris_lines.append(f"UR  - {paper.url}")

    if paper.arxiv_id:
        ris_lines.append(f"M1  - arXiv:{paper.arxiv_id}")

    ris_lines.append("ER  - ")
    return "\n".join(ris_lines) + "\n"


def paper_to_csl_json(paper: Paper) -> dict:
    """Convert a paper to CSL-JSON format."""
    csl_item = {
        "id": paper.id,
        "type": "article-journal" if not paper.arxiv_id else "report"
    }

    if paper.title:
        csl_item["title"] = paper.title

    if paper.authors:
        csl_item["author"] = [
            {"family": author.name.split()[-1], "given": " ".join(author.name.split()[:-1])}
            for author in paper.authors if author.name
        ]

    if paper.published_date:
        csl_item["issued"] = {
            "date-parts": [[
                paper.published_date.year,
                paper.published_date.month or 1,
                paper.published_date.day or 1
            ]]
        }

    if paper.venue:
        if paper.arxiv_id:
            csl_item["publisher"] = paper.venue
        else:
            csl_item["container-title"] = paper.venue

    if paper.abstract:
        csl_item["abstract"] = paper.abstract

    if paper.doi:
        csl_item["DOI"] = paper.doi

    if paper.url:
        csl_item["URL"] = paper.url

    if paper.arxiv_id:
        csl_item["number"] = paper.arxiv_id
        csl_item["genre"] = "preprint"

    return csl_item


def export_papers(papers: List[Paper], format_type: str) -> ExportFormat:
    """Export papers in the specified format."""
    if format_type.lower() == "bibtex":
        content = "\n".join([paper_to_bibtex(paper) for paper in papers])
        return ExportFormat(format_type="bibtex", content=content)

    elif format_type.lower() == "ris":
        content = "\n".join([paper_to_ris(paper) for paper in papers])
        return ExportFormat(format_type="ris", content=content)

    elif format_type.lower() == "csl-json":
        csl_items = [paper_to_csl_json(paper) for paper in papers]
        content = json.dumps(csl_items, indent=2)
        return ExportFormat(format_type="csl-json", content=content)

    else:
        raise ValueError(f"Unsupported export format: {format_type}")