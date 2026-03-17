# ADR-001: RAG Design Decisions

## Status

Accepted (v0.2.0)

## Context

PubSave v0.2.0 adds semantic search and question-answering over saved papers. This required choosing a distance metric, an embedding granularity, and an index type for pgvector.

## Decisions

### 1. Cosine similarity over inner product

**Chosen**: Cosine distance (`<=>` operator in pgvector)

OpenAI's text-embedding-3-small produces normalized vectors, so cosine and inner product give identical rankings. We went with cosine because it's the more widely understood metric, and anyone reading the SQL can immediately tell what the query does. If we later switch to an embedding provider that doesn't normalize, cosine still works correctly without reindexing.

Inner product (`<#>`) would save a negligible amount of computation on already-normalized vectors, but the readability tradeoff isn't worth it.

### 2. Whole-abstract embedding over chunking

**Chosen**: Embed the full abstract as a single vector per paper.

PubMed abstracts are typically 200-400 words, well within the 8191-token context window of text-embedding-3-small. Chunking would add complexity (chunk overlap, reassembly, mapping chunks back to papers) for no quality gain at this document size.

If PubSave later ingests full-text PDFs or longer documents, chunking becomes necessary. For now, one vector per paper keeps the data model simple: `papers.embedding` is a single column, and search returns whole papers rather than fragments.

### 3. HNSW over IVFFlat

**Chosen**: HNSW index (`CREATE INDEX ... USING hnsw`)

At the scale PubSave operates (hundreds to low thousands of papers for a personal collection), both index types are fast enough. We chose HNSW because:

- It doesn't require a separate training step. IVFFlat needs `CREATE INDEX` to scan the existing data and build clusters, and the index quality degrades if you add significantly more data after creation without rebuilding.
- HNSW handles incremental inserts well. Papers get added one at a time via `pubsave fetch`, and the index stays balanced without maintenance.
- Query performance is better for small to medium datasets. IVFFlat needs enough data to fill its clusters before it outperforms a sequential scan.

The tradeoff is that HNSW uses more memory than IVFFlat and has slower index builds. Neither matters at personal-collection scale.

### 4. Question before context in RAG prompt

**Chosen**: Question first, then paper abstracts.

The prompt format is:

```
Question: {user's question}

Papers:
[PMID:12345678] Title
Abstract text...

[PMID:87654321] Title
Abstract text...
```

Most RAG implementations put context first so the question sits closest to where the model starts generating. We tried both orderings during development and found no meaningful quality difference at the abstract lengths we work with. The question-first format reads more naturally when debugging prompts, so we kept it. If answer quality becomes an issue with larger context windows, flipping the order is a one-line change in `service.py`.

### 5. System prompt in service, not LLM client

**Chosen**: `RAG_SYSTEM_PROMPT` constant in `PaperService`, LLM client signature is `generate(system, user) -> str`.

The LLM client is pure transport. It doesn't know what it's being used for. The service layer owns the prompt because prompt construction is business logic: which PMIDs to include, how to format abstracts, what citation format to request. This keeps the LLM client reusable across different features without modification, and makes the prompt testable by inspecting `call_args` in unit tests.
