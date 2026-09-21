# CV Screener

Generates a synthetic dataset of candidate resumes (PDF + photo + structured
data), indexes it for both field and semantic search, and answers questions
about the dataset through a tool-calling chat agent — CLI only, OpenAI only.

## What's here

| Piece | Command | What it does |
|---|---|---|
| 1. Resume generation | `cvscreener generate --n 12` | Builds N diverse synthetic candidates: structured profile (Faker + curated role/company/education pools), an LLM-written summary (`gpt-4o-mini`), an AI headshot (`gpt-image-1`), and a one-page PDF resume (`fpdf2`). |
| 2. Indexing + search | `cvscreener index`, `cvscreener search` | Embeds each candidate (`text-embedding-3-small`) into pgvector alongside structured fields; search works by field, by meaning, or both. |
| 3. Chat agent | `cvscreener chat` | A `gpt-4o-mini` tool-calling agent that answers questions about the dataset by calling search tools — it never gets the dataset dumped into its prompt. |

## Requirements

- Python 3.11+ (tested on 3.11; **not** 3.14 — see note below)
- [Poetry](https://python-poetry.org/)
- Docker Desktop (for the Postgres/pgvector container)
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

# 2. Start Postgres with the pgvector extension
docker compose up -d

# 3. Install Python dependencies (creates a venv managed by Poetry)
poetry install

# 4. Configure your API key
cp .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-...
# (DATABASE_URL in .env.example already matches docker-compose.yml)
```

## Run it

Each step is one command:

```bash
# Generate >=10 synthetic candidates (writes to data/profiles, data/photos, data/resumes)
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

25 tests, all runnable **without** an API key and **without** a running
database (verified with `OPENAI_API_KEY=` unset and no `docker compose up`).
They cover the Pydantic schema, PDF rendering (including the Latin-1
Unicode-sanitization edge case), the structured-field query builder, and
the agent's tool wrappers (with the search/DB layer mocked out).

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

## Cost

Budget target was $2-5. Actual spend for `--n 12` generation (12x
`gpt-4o-mini` summary calls + 12x `gpt-image-1` low-quality 1024x1024
headshots + 12 embeddings) plus the full eval run came in well under $1 —
see `NOTES.md` for the breakdown.

## Repo layout

```
src/cv_screener/
  schemas.py           CandidateProfile Pydantic model (embedding_text/metadata)
  config.py             env loading, paths, model names
  db.py                   SQLAlchemy engine + the `candidates` structured-fields table
  generation/
    pools.py                curated roles/companies/universities/languages for diversity
    profiles.py               Faker + pools sampling, gpt-4o-mini summary prose
    photos.py                  gpt-image-1 headshot generation
    pdf_render.py                fpdf2 one-page resume layout
  indexing/
    vectorstore.py             PGVector + OpenAIEmbeddings setup
    build_index.py               loads profiles -> populates both stores
    search.py                     semantic_search / filter_search / hybrid_search
    filters.py                     pure, DB-free query-builder functions
  agent/
    tools.py                     the 3 LangChain tools the agent calls
    chat_agent.py                  manual tool-call loop + system prompt
  cli.py                            Typer app: generate / index / search / chat
evals/
  cases.yaml, run_evals.py         6 question/expectation cases, pass/fail runner
tests/                              25 tests, no API key / DB required
```

## What I'd do next

See `NOTES.md`.
