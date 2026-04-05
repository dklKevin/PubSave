# Getting Started with PubSave

A 5-minute walkthrough from zero to asking questions about your saved papers.

## Setup

You need Docker, Docker Compose, and Python 3.12+.

```bash
git clone https://github.com/dklKevin/PubSave.git
cd PubSave
cp .env.example .env
```

Open `.env` and fill in your database credentials. Add your OpenAI API key if you want semantic search and question-answering (you can skip this and add it later).

```bash
# .env
DB_USER=pubsave
DB_PASSWORD=pick_something_strong
DB_NAME=pubsave
OPENAI_API_KEY=sk-proj-...   # optional
```

Start the stack and install the CLI:

```bash
docker compose up -d
pip install -e .
```

The API is now running at `http://localhost:8000`. Migrations run automatically on first boot.

## Save your first paper

Every paper on PubMed has an ID (the PMID). You can find it in the URL or on the paper's page. Pass it to `pubsave fetch`:

```bash
pubsave fetch 33057194
```

PubSave pulls the title, authors, abstract, journal, DOI, and publication date from PubMed and saves everything to your database. If you have an OpenAI key configured, the abstract is embedded automatically for semantic search.

## Browse your collection

```bash
# list all saved papers
pubsave ls

# view a specific paper (use the first 6+ characters of its ID)
pubsave get a1b2c3
```

Short IDs work everywhere. You never need to type a full UUID.

## Search

Keyword search works across titles, abstracts, and authors:

```bash
pubsave search microbiome
pubsave search -a Zhang
```

If you have an OpenAI key, semantic search finds papers by meaning rather than exact keywords:

```bash
pubsave search --semantic "gene therapy for rare diseases"
```

This finds relevant papers even if they never use the phrase "gene therapy."

## Organize with tags

Tags are freeform. Add as many as you want:

```bash
pubsave tag a1b2c3 genetics to-read important
```

Then search by tag:

```bash
pubsave search -t genetics
```

Remove a tag when you're done with it:

```bash
pubsave untag a1b2c3 to-read
```

See all tags across your collection:

```bash
pubsave tags
```

## Ask questions (RAG)

This is the headline feature of v0.2.0. Ask a question and get an answer grounded in your saved papers:

```bash
pubsave ask "What are the main findings on CRISPR delivery methods?"
```

PubSave embeds your question, finds the most relevant papers by cosine similarity, feeds their abstracts to the LLM, and returns an answer with PMID citations you can verify. The response includes which papers were used and their relevance scores.

This requires an OpenAI API key. Without one, the command returns a 503 error. Everything else (fetch, search, tag) works without a key.

## Backfill embeddings

If you saved papers before adding your OpenAI key, backfill their embeddings in one command:

```bash
pubsave embed-all
```

This processes papers in batches. Once embedded, they show up in semantic search and are available as context for `ask`.

## CLI options

Every command supports these flags:

| Flag | What it does |
|------|--------------|
| `--json` | Raw JSON output (useful for scripting) |
| `--full` | Show full paper details instead of the compact view |
| `--page N` | Pagination page number |
| `--limit N` | Results per page |

Point the CLI at a different server with `PUBSAVE_URL`:

```bash
PUBSAVE_URL=http://192.168.1.50:8000 pubsave ls
```

## Using the API directly

The CLI wraps a REST API. You can call it directly with curl:

```bash
# fetch a paper
curl -X POST http://localhost:8000/api/v1/papers/fetch/33057194

# list papers
curl http://localhost:8000/api/v1/papers

# semantic search
curl "http://localhost:8000/api/v1/papers/search/semantic?q=gene+therapy"

# ask a question
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main CRISPR delivery methods?", "top_k": 5}'
```

Full endpoint list is in the README.

## Next steps

Save a few papers you're actually reading, tag them by project or topic, and try asking questions across them. The more papers you save, the better the answers get.
