# CV Screener

Generates a synthetic dataset of candidate resumes (PDF + photo + structured
data), indexes it for both field and semantic search, and answers questions
about the dataset through a tool-calling chat agent — CLI only, OpenAI only.

## What's here

| Piece | Command | What it does |
|---|---|---|
| 1. Resume generation | `cvscreener generate --n 12` | Builds N diverse synthetic candidates: structured profile (Faker + curated role/company/education pools), an LLM-written summary (`gpt-4o-mini`), an AI headshot (`gpt-image-1`), and a one-page PDF resume (`fpdf2`). Photos and PDFs are uploaded straight to S3-compatible object storage. |
| 2. Indexing + search | `cvscreener index`, `cvscreener search` | Embeds each candidate (`text-embedding-3-small`) into pgvector alongside structured fields; search works by field, by meaning, or both. |
| 3. Chat agent | `cvscreener chat` | A `gpt-4o-mini` tool-calling agent that answers questions about the dataset by calling search tools — it never gets the dataset dumped into its prompt. |

Candidate profile JSON (structured fields) lives in `data/profiles/`; the
binary photo and PDF assets live in object storage, not on local disk —
see "Object storage" below.

## Requirements

- Python 3.11+ (tested on 3.11; **not** 3.14 — see note below)
- [Poetry](https://python-poetry.org/)
- Docker Desktop (for the Postgres/pgvector and object-storage containers)
- An OpenAI API key

> **Python version note:** this project was built and tested against Python
> 3.11. If your default `python`/`poetry env use python` resolves to 3.14,
> `numpy`'s pinned build (required transitively by `langchain-postgres`)
> has no prebuilt wheel for 3.14 yet and will fail to build without a C
> compiler. Point Poetry at 3.11 explicitly if needed:
> `poetry env use "C:\Path\To\Python311\python.exe"` (Windows) or
> `poetry env use python3.11` (macOS/Linux).

## Setup, from scratch

```bash
# 1. Clone and enter the repo
cd cv-screener

# 2. Start Postgres (pgvector) and object storage (pgsty/minio)
docker compose up -d

# 3. Install Python dependencies (creates a venv managed by Poetry)
poetry install

# 4. Configure your API key
cp .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-...
# (DATABASE_URL/S3_* in .env.example already match docker-compose.yml)
```

## Run it

Each step is one command:

```bash
# Generate >=10 synthetic candidates (profile JSON -> data/profiles/,
# photos + PDF resumes -> object storage)
poetry run cvscreener generate --n 12

# Build the search index (structured fields -> Postgres table, embeddings -> pgvector)
poetry run cvscreener index

# Try search directly (optional, sanity check independent of the agent)
poetry run cvscreener search "backend engineer with strong Python and API experience"
poetry run cvscreener search --field languages --value Spanish
poetry run cvscreener search "senior candidate" --field seniority --value senior

# Chat with the agent
poetry run cvscreener chat
```

Example session:

```
$ poetry run cvscreener chat
CV Screener chat. Ask about the candidates. Type 'exit' to quit.

> Who has experience with Python?
The following candidates have experience with Python: ...

> Which candidates speak Spanish?
The candidate who speaks Spanish is: Amy Brown - Mobile Engineer (junior) ...

> exit
```

### `cvscreener generate` options

- `--n INTEGER` — number of candidates (default 10; the task requires >=10)
- `--seed INTEGER` — random seed for reproducible sampling of roles/companies/etc.
  (the LLM-written prose still varies run to run)

### `cvscreener search` options

- `QUERY` (positional, optional) — natural-language query for semantic search
- `--field` / `--value` — structured-field filter (see valid fields below)
- both together — hybrid: filter first, then rank the survivors by similarity to `QUERY`
- `--k INTEGER` — max results (default 5)

Valid `--field` values: `full_name`, `role`, `seniority`, `location`,
`skills`, `languages`, `companies`, `years_of_experience` (supports `5`,
`>=5`, `>5`, `<=5`, `<5`).

## Object storage

Generated photos and PDF resumes are uploaded to S3-compatible object
storage rather than written to local disk. `docker-compose.yml` runs
**`pgsty/minio`** — a community-maintained fork of MinIO
([pgsty/silo](https://github.com/pgsty/silo)) — instead of `minio/minio`,
because MinIO stopped publishing free Docker images in October 2025 and
later archived the repo entirely. The app only talks to it over the
standard S3 API via `boto3`, so nothing is actually MinIO-specific; the
`S3_*` variables in `.env` would work unchanged against real AWS S3 or any
other S3-compatible service.

- Browse everything at the web console: **http://localhost:9001**
  (credentials: `S3_ACCESS_KEY` / `S3_SECRET_KEY` from `.env`).
- Bucket layout: `photos/{candidate_id}.png`, `resumes/{candidate_id}.pdf`.
- `cvscreener migrate-storage` is a one-time command for a dataset
  generated before this feature existed: it uploads any local
  `data/photos/*.png` / `data/resumes/*.pdf` still referenced by a profile,
  updates that profile's JSON to point at the new object key, deletes the
  local file once the upload is verified, and is safe to re-run (already
  S3-backed profiles are skipped). Run `cvscreener index` afterwards to
  refresh the metadata cached in Postgres/pgvector.

## Evals

```bash
poetry run python evals/run_evals.py
```

Runs 6 question/expectation pairs against the real agent (calls the OpenAI
API) and prints PASS/FAIL per case plus a final tally. See `NOTES.md` for
the actual recorded output of the last run.

## Tests

```bash
poetry run pytest
```

31 tests, all runnable **without** an API key and **without** a running
database or object storage (verified with `OPENAI_API_KEY=` unset and no
`docker compose up`). They cover the Pydantic schema, PDF rendering
(including the Latin-1 Unicode-sanitization edge case and in-memory photo
embedding), the structured-field query builder, the S3 client wrapper (with
`boto3` mocked out), and the agent's tool wrappers (with the search/DB
layer mocked out).

## Architecture notes

- **Two stores, one purpose split.** `langchain_postgres.PGVector` owns the
  embeddings + a jsonb copy of each candidate's metadata (semantic search).
  A plain `candidates` SQL table (`db.py`) owns the same structured fields
  as real columns (field search). This keeps field search simple, fast SQL
  `WHERE` clauses instead of reaching into langchain's internal table
  schema, while both stores are rebuilt together by `cvscreener index`.
- **The agent never sees the dataset.** `agent/chat_agent.py` runs a manual
  tool-call loop (ask the model -> if it calls a tool, run it and feed the
  result back -> repeat) against three tools in `agent/tools.py`:
  `semantic_search_tool`, `filter_search_tool`, `get_candidate_profile_tool`.
  The system prompt requires a tool call before every answer and requires
  naming real candidates; `evals/run_evals.py` checks this by inspecting
  the message history for at least one `ToolMessage`, not just parsing the
  final answer text.
- **`indexing/filters.py` is pure and DB-free.** It builds SQLAlchemy filter
  expressions from `CandidateRow` columns without opening a connection,
  which is what makes `tests/test_filters.py` runnable with zero
  infrastructure.
- **Photos never touch local disk.** `generation/photos.py` uploads the
  resized headshot straight to object storage and hands the same in-memory
  `PIL.Image` to `pdf_render.py`, which embeds it directly and returns raw
  PDF bytes for `cli.py` to upload — no temp files, no re-download.

## Cost

Budget target was $2-5. Actual spend across both generation batches (24
candidates total: `gpt-4o-mini` summaries + `gpt-image-1` low-quality
1024x1024 headshots + embeddings) plus multiple eval runs came in well
under $1-2 — see `NOTES.md` for the breakdown. Object storage and Postgres
are self-hosted via Docker, so they cost nothing beyond local disk.

## Repo layout

```
src/cv_screener/
  schemas.py           CandidateProfile Pydantic model (embedding_text/metadata)
  config.py             env loading, paths, model names, S3 settings
  db.py                   SQLAlchemy engine + the `candidates` structured-fields table
  storage.py               S3 client wrapper (boto3) for photos + PDF resumes
  generation/
    pools.py                curated roles/companies/universities/languages for diversity
    profiles.py               Faker + pools sampling, gpt-4o-mini summary prose
    photos.py                  gpt-image-1 headshot generation -> uploaded to storage
    pdf_render.py                fpdf2 one-page resume layout, returns PDF bytes
  indexing/
    vectorstore.py             PGVector + OpenAIEmbeddings setup
    build_index.py               loads profiles -> populates both stores
    search.py                     semantic_search / filter_search / hybrid_search
    filters.py                     pure, DB-free query-builder functions
  agent/
    tools.py                     the 3 LangChain tools the agent calls
    chat_agent.py                  manual tool-call loop + system prompt
  cli.py                            Typer app: generate / migrate-storage / index / search / chat
evals/
  cases.yaml, run_evals.py         6 question/expectation cases, pass/fail runner
tests/                              31 tests, no API key / DB / storage required
```

## What I'd do next

See `NOTES.md`.
