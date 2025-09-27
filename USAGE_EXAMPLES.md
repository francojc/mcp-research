# MCP Research Server Usage Examples

## Table of Contents

- [Basic Search Examples](#basic-search-examples)
- [Advanced Search Examples](#advanced-search-examples)
- [Author Research Examples](#author-research-examples)
- [Citation Analysis Examples](#citation-analysis-examples)
- [Bibliography Management Examples](#bibliography-management-examples)
- [AI Recommendations Examples](#ai-recommendations-examples)
- [System Management Examples](#system-management-examples)
- [Research Workflow Examples](#research-workflow-examples)

## Basic Search Examples

### Simple Topic Search

**Scenario**: You want to find papers about machine learning.

```
search_papers(
    query="machine learning",
    max_results=10,
    sources="arxiv,semantic_scholar"
)
```

**Expected Output**: A list of 10 papers about machine learning with titles, authors, abstracts, and citation counts.

### Multi-term Search

**Scenario**: Looking for papers that combine natural language processing and deep learning.

```
search_papers(
    query="natural language processing deep learning",
    max_results=15,
    sources="arxiv,semantic_scholar,google_scholar"
)
```

**Use Case**: Literature review for interdisciplinary research.

### Specific Technology Search

**Scenario**: Finding papers about transformer architectures.

```
search_papers(
    query="transformer attention mechanism",
    max_results=20,
    sources="arxiv,semantic_scholar"
)
```

## Advanced Search Examples

### Field-Specific Advanced Search

**Scenario**: Looking for papers with "BERT" in the title by authors affiliated with Google, published between 2018-2023.

```
advanced_search_papers(
    title="BERT",
    author="google",
    year_start=2018,
    year_end=2023,
    sources="arxiv,semantic_scholar",
    max_results=15
)
```

**Use Case**: Tracking specific model developments at particular institutions.

### Conference-Specific Search

**Scenario**: Finding computer vision papers from NeurIPS conference.

```
advanced_search_papers(
    keywords="computer vision",
    venue="NeurIPS",
    year_start=2020,
    year_end=2023,
    sources="semantic_scholar",
    max_results=25
)
```

**Use Case**: Conference paper analysis and trend identification.

### Abstract Content Search

**Scenario**: Looking for papers that mention specific techniques in their abstracts.

```
advanced_search_papers(
    abstract="graph neural networks attention",
    year_start=2021,
    sources="arxiv",
    max_results=20
)
```

## Author Research Examples

### Single Author Research

**Scenario**: Finding all papers by Yann LeCun.

```
search_author_papers(
    author_name="Yann LeCun",
    max_results=30,
    sources="arxiv,semantic_scholar,google_scholar"
)
```

**Use Case**: Comprehensive author bibliography creation.

### Multiple Authors Collaboration

**Scenario**: Finding collaborative work between specific researchers.

```
search_papers(
    query="Yoshua Bengio Geoffrey Hinton",
    max_results=10,
    sources="semantic_scholar"
)
```

**Use Case**: Analyzing research collaborations and networks.

### Institution Research

**Scenario**: Finding recent AI papers from MIT.

```
advanced_search_papers(
    keywords="artificial intelligence",
    author="MIT",
    year_start=2022,
    sources="arxiv,semantic_scholar",
    max_results=25
)
```

## Citation Analysis Examples

### Paper Impact Analysis

**Scenario**: Finding papers that cite the original transformer paper.

```
get_citations(
    paper_id="10.48550/arXiv.1706.03762",
    source="semantic_scholar",
    max_results=50
)
```

**Use Case**: Understanding the impact and influence of seminal papers.

### Citation Chain Analysis

**Scenario**: Tracing the citation lineage of a paper.

```
# Step 1: Get the original paper details
get_paper_details(paper_id="attention is all you need", source="semantic_scholar")

# Step 2: Get papers that cite it
get_citations(paper_id="[paper_id_from_step1]", max_results=20)

# Step 3: Get details of highly cited papers from step 2
get_paper_details(paper_id="[highly_cited_paper_id]")
```

**Use Case**: Literature review and understanding research evolution.

## Bibliography Management Examples

### BibTeX Export for LaTeX

**Scenario**: Exporting search results to BibTeX format for a LaTeX document.

```
# First, search for papers
search_papers(query="reinforcement learning robotics", max_results=15)

# Then export to BibTeX
export_bibliography(
    papers="[comma-separated paper IDs from search results]",
    format="bibtex",
    output_file="~/Documents/research/robotics_rl.bib"
)
```

**Use Case**: Academic paper writing and citation management.

### Multi-format Bibliography

**Scenario**: Creating bibliography in multiple formats for different submission requirements.

```
# Export to BibTeX for LaTeX
export_bibliography(
    papers="paper1,paper2,paper3",
    format="bibtex",
    output_file="references.bib"
)

# Export to RIS for reference managers
export_bibliography(
    papers="paper1,paper2,paper3",
    format="ris",
    output_file="references.ris"
)

# Export to JSON for custom processing
export_bibliography(
    papers="paper1,paper2,paper3",
    format="csl_json",
    output_file="references.json"
)
```

### Dynamic Bibliography from Search

**Scenario**: Creating a bibliography directly from a search query without manually specifying paper IDs.

```
export_bibliography(
    papers="quantum computing error correction",
    format="bibtex",
    output_file="quantum_refs.bib"
)
```

**Use Case**: Quick bibliography generation for specific topics.

## AI Recommendations Examples

### Content-Based Recommendations

**Scenario**: Finding papers similar to a known paper based on content.

```
recommend_papers(
    seed_papers="BERT: Pre-training of Deep Bidirectional Transformers",
    method="content",
    max_recommendations=10,
    sources="arxiv,semantic_scholar"
)
```

**Use Case**: Finding related work for literature review.

### Citation-Based Recommendations

**Scenario**: Finding influential papers in the same field.

```
recommend_papers(
    seed_papers="ImageNet classification with deep convolutional neural networks",
    method="citations",
    max_recommendations=15,
    sources="semantic_scholar"
)
```

**Use Case**: Finding highly-cited foundational papers.

### Hybrid Recommendations

**Scenario**: Getting comprehensive recommendations combining multiple factors.

```
recommend_papers(
    seed_papers="graph neural networks node classification",
    method="hybrid",
    max_recommendations=12,
    sources="arxiv,semantic_scholar"
)
```

**Use Case**: Comprehensive related work discovery.

### Multi-paper Seed Recommendations

**Scenario**: Getting recommendations based on multiple seed papers.

```
# Use multiple paper IDs as seeds
recommend_papers(
    seed_papers="paper_id_1,paper_id_2,paper_id_3",
    method="hybrid",
    max_recommendations=15
)
```

**Use Case**: Finding papers that bridge multiple research areas.

## System Management Examples

### Cache Performance Monitoring

**Scenario**: Checking cache performance to optimize system usage.

```
manage_cache(action="stats")
```

**Expected Output**:
```
📊 Cache Statistics
• Total entries: 1,247
• Cache hits: 892 (71.5%)
• Cache misses: 355 (28.5%)
• Total size: 15.3 MB
```

**Use Case**: System performance monitoring and optimization.

### Cache Maintenance

**Scenario**: Regular cache cleanup to maintain system performance.

```
# Clean expired entries
manage_cache(action="cleanup")

# If needed, completely clear cache
manage_cache(action="clear")
```

**Use Case**: System maintenance and troubleshooting.

## Research Workflow Examples

### Literature Review Workflow

**Scenario**: Conducting a comprehensive literature review on "federated learning".

```
# Step 1: Initial broad search
search_papers(
    query="federated learning",
    max_results=20,
    sources="arxiv,semantic_scholar,google_scholar"
)

# Step 2: Get recommendations based on key papers found
recommend_papers(
    seed_papers="federated learning survey",
    method="hybrid",
    max_recommendations=15
)

# Step 3: Find seminal papers through citations
get_citations(
    paper_id="[key_paper_id_from_step1]",
    max_results=30
)

# Step 4: Search for recent developments
advanced_search_papers(
    title="federated learning",
    year_start=2022,
    year_end=2023,
    max_results=25
)

# Step 5: Export comprehensive bibliography
export_bibliography(
    papers="[all_relevant_paper_ids]",
    format="bibtex",
    output_file="federated_learning_review.bib"
)
```

### Author Collaboration Analysis

**Scenario**: Analyzing collaboration patterns in deep learning research.

```
# Step 1: Find papers by key researchers
search_author_papers(author_name="Yoshua Bengio", max_results=25)
search_author_papers(author_name="Geoffrey Hinton", max_results=25)
search_author_papers(author_name="Yann LeCun", max_results=25)

# Step 2: Look for collaborative papers
search_papers(
    query="Bengio Hinton deep learning",
    max_results=15,
    sources="semantic_scholar"
)

# Step 3: Analyze citation patterns
get_citations(paper_id="[collaboration_paper_id]", max_results=50)
```

### Conference Paper Discovery

**Scenario**: Finding the most relevant papers from recent ML conferences.

```
# Step 1: Search recent NeurIPS papers
advanced_search_papers(
    venue="NeurIPS",
    year_start=2022,
    year_end=2023,
    max_results=30
)

# Step 2: Search ICML papers
advanced_search_papers(
    venue="ICML",
    year_start=2022,
    year_end=2023,
    max_results=30
)

# Step 3: Get recommendations based on interesting papers
recommend_papers(
    seed_papers="[interesting_paper_ids]",
    method="content",
    max_recommendations=20
)
```

### Trend Analysis Workflow

**Scenario**: Analyzing trends in "large language models" research.

```
# Step 1: Historical perspective
advanced_search_papers(
    title="language models",
    year_start=2018,
    year_end=2020,
    max_results=20
)

# Step 2: Recent developments
advanced_search_papers(
    title="large language models",
    year_start=2021,
    year_end=2023,
    max_results=30
)

# Step 3: Get highly cited recent papers
search_papers(
    query="GPT BERT T5 large language models",
    max_results=25,
    sources="semantic_scholar"
)

# Step 4: Analyze what's citing recent breakthrough papers
get_citations(paper_id="[breakthrough_paper_id]", max_results=40)
```

## Query Optimization Examples

### Natural Language Query Building

**Scenario**: Converting research questions to optimized queries.

```
# Research question: "What are the latest techniques for few-shot learning in computer vision?"
build_search_query(
    natural_language="latest techniques few-shot learning computer vision",
    target_source="arxiv"
)
```

**Expected Output**: Optimized arXiv query with appropriate field prefixes and Boolean operators.

### Multi-source Query Optimization

**Scenario**: Building queries optimized for different sources.

```
# For arXiv (more structured)
build_search_query(
    natural_language="transformer models for time series forecasting",
    target_source="arxiv"
)

# For Google Scholar (broader approach)
build_search_query(
    natural_language="transformer models for time series forecasting",
    target_source="google_scholar"
)
```

## Error Handling Examples

### Graceful Failure Recovery

**Scenario**: When one source fails, continue with others.

```
# This will automatically handle source failures gracefully
search_papers(
    query="quantum machine learning",
    max_results=20,
    sources="arxiv,semantic_scholar,google_scholar"
)
```

**Expected Behavior**: If one source fails, results from other sources are still returned with appropriate error notifications.

### Rate Limit Handling

**Scenario**: When hitting API rate limits, the system automatically retries with backoff.

```
# Multiple rapid searches will trigger intelligent retry mechanisms
search_papers(query="search 1", max_results=10)
search_papers(query="search 2", max_results=10)
search_papers(query="search 3", max_results=10)
```

**Expected Behavior**: System automatically manages rate limits and retries with exponential backoff.

## Advanced Use Cases

### Meta-Research Analysis

**Scenario**: Analyzing research patterns and trends across fields.

```
# Step 1: Get papers from different AI subfields
ai_papers = search_papers(query="artificial intelligence", max_results=100)
ml_papers = search_papers(query="machine learning", max_results=100)
dl_papers = search_papers(query="deep learning", max_results=100)

# Step 2: Analyze cross-citations
get_citations(paper_id="[representative_ai_paper]", max_results=100)

# Step 3: Find interdisciplinary papers
search_papers(query="AI machine learning deep learning", max_results=50)
```

### Research Impact Assessment

**Scenario**: Measuring the impact of research over time.

```
# Step 1: Find a seminal paper
seminal_paper = search_papers(query="dropout regularization neural networks", max_results=5)

# Step 2: Track its citations over time
citations = get_citations(paper_id="[seminal_paper_id]", max_results=200)

# Step 3: Analyze citing papers' impact
# (Manually analyze citation counts and venues of citing papers)
```

### Competitive Research Analysis

**Scenario**: Analyzing what competitors or other research groups are working on.

```
# Step 1: Find recent papers from specific institutions
advanced_search_papers(
    author="OpenAI",
    year_start=2023,
    max_results=20
)

# Step 2: Get recommendations based on their work
recommend_papers(
    seed_papers="[their_recent_papers]",
    method="content",
    max_recommendations=25
)

# Step 3: Find who's citing their work
get_citations(paper_id="[their_key_paper]", max_results=50)
```

## Performance Tips

### Efficient Search Strategies

1. **Start Broad, Then Narrow**:
   ```
   # Step 1: Broad search
   search_papers(query="machine learning", max_results=50)

   # Step 2: Narrow based on findings
   advanced_search_papers(
       title="supervised learning",
       year_start=2020,
       max_results=20
   )
   ```

2. **Use Appropriate Sources**:
   ```
   # For CS/AI papers: prioritize arXiv
   search_papers(query="neural networks", sources="arxiv")

   # For citation analysis: use Semantic Scholar
   get_citations(paper_id="paper_id", source="semantic_scholar")

   # For comprehensive coverage: use all sources
   search_papers(query="interdisciplinary topic", sources="arxiv,semantic_scholar,google_scholar")
   ```

3. **Leverage Caching**:
   ```
   # Repeated similar queries benefit from caching
   search_papers(query="transformers", max_results=20)  # First call: API request
   search_papers(query="transformers", max_results=20)  # Second call: cached result
   ```

4. **Batch Related Operations**:
   ```
   # Instead of multiple individual calls, batch when possible
   papers = search_papers(query="topic", max_results=20)
   # Then use paper IDs from results for exports, citations, etc.
   ```

These examples demonstrate the comprehensive capabilities of the MCP Research Server and how to use them effectively for various research scenarios. Each example includes the specific use case and expected outcomes to help users understand when and how to apply different tools.