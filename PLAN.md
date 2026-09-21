# CV Screener — Development Plan

Test task: synthetic resume generation, vector + field search, and a tool-using
chat agent over the dataset. Python only; stack choices below are mine.

Provider: **OpenAI only** — `gpt-4o-mini` for resume prose and the chat agent,
`gpt-image-1` for headshots, `text-embedding-3-small` for embeddings. One API
key (`OPENAI_API_KEY`) covers everything.

Vector store: **pgvector** (Postgres + the `pgvector` extension), run via
Docker Compose, accessed through LangChain's `langchain-postgres` `PGVector`
store.

## Repo layout

```
Task/
  pyproject.toml
  README.md            # setup + run instructions, from scratch
  CLAUDE.md
  NOTES.md
  .env.example
  .gitignore
  docker-compose.yml     # single `db` service: pgvector/pgvector:pg16
  data/
    profiles/             # generated candidate JSON (structured fields)
    resumes/               # generated PDF resumes
    photos/                 # generated headshots (PNG)
  src/cv_screener/
    schemas.py               # Pydantic CandidateProfile model
    db.py                      # SQLAlchemy engine / connection string helper
    generation/
      profiles.py               # synthetic profile builder (Faker + curated pools + LLM prose)
      photos.py                   # gpt-image-1 headshot generation
      pdf_render.py                 # fpdf2-based resume layout (photo + sections)
    indexing/
      vectorstore.py                 # PGVector store setup, embeddings, add/query
      build_index.py                   # loads profiles -> embeds -> upserts into pgvector
      search.py                          # hybrid: metadata filter + semantic similarity
      filters.py                          # pure filter/query-builder functions (DB-free, unit-testable)
    agent/
      tools.py                             # LangChain tools: semantic_search, filter_search, get_profile
      chat_agent.py                          # tool-calling agent (LangChain + ChatOpenAI)
    cli.py                                    # Typer app: generate / index / search / chat
  templates/ (prompt templates for profile prose, kept as .txt/.jinja)
  evals/
    cases.yaml                                 # >=5 question -> expected candidate(s)/behavior
    run_evals.py                                 # runs agent, prints pass/fail per case + summary
  tests/
    test_schemas.py                               # no API key, no DB
    test_pdf_render.py                              # no API key, no DB
    test_filters.py                                  # filter/query-builder logic, no API key, no DB
    test_agent_tools.py                               # tool selection logic with a stub/mock LLM, no DB
    conftest.py
```

## 1. Resume generation (`cvscreener generate`)

- **Diversity engine**: curated pools (10+ roles from junior QA to senior
  ML/staff eng to PM/designer, 4 seniority bands, varied tech stacks,
  fictional companies, universities/degrees, language sets, locations).
  Faker fills names/contact details; a sampler picks a coherent combination
  per candidate (seniority drives years of experience and company count) so
  candidates aren't reskins of one template.
- **Prose**: one `gpt-4o-mini` call per candidate turns the structured facts
  into a natural summary + experience bullets + skills phrasing.
- **Photo**: one `gpt-image-1` call per candidate (small size, low quality
  tier) generates a headshot matching the implied age/role — generated, not
  stock/scraped. Cost stays well under a cent per image.
- **Rendering**: `fpdf2` (pure Python, no system dependencies — avoids
  WeasyPrint's GTK install pain on Windows) lays out a one-page resume:
  header with photo, contact info, summary, experience, education, skills,
  languages.
- Structured JSON profile is saved next to the PDF so indexing doesn't need
  to re-parse it.
- One command: `cvscreener generate --n 12` produces JSON + PDF + photo per
  candidate.

## 2. Indexing and search (`cvscreener index`, `cvscreener search`)

- **Infra**: `docker-compose.yml` defines one `db` service
  (`pgvector/pgvector:pg16`) with a named volume and healthcheck. README
  step 1 is `docker compose up -d`; everything after that is the app's own
  single commands.
- **Store**: `langchain-postgres` `PGVector`, connected via `DATABASE_URL`
  (`postgresql+psycopg://cvscreener:cvscreener@localhost:5432/cvscreener`).
  The table/collection is created automatically on first index build.
- **Documents**: embedding text = generated summary + experience + skills
  prose (captures semantic meaning); **metadata** (jsonb column) = structured
  fields — role, seniority, years_of_experience, skills list, languages,
  companies, education, location — for exact/filtered lookup.
- **Search modes**, in `indexing/search.py`:
  - metadata filter (e.g. `languages @> '["Spanish"]'`, `role = "ML Engineer"`)
  - semantic similarity (embed the query, pgvector nearest-neighbor via
    cosine distance)
  - hybrid: filter first (SQL `WHERE` on metadata), then rank the remaining
    rows by similarity
- Filter/query construction lives in `indexing/filters.py` as pure functions
  (dict/SQL-clause builders) with no DB connection, so this logic is
  unit-testable without Postgres running.
- `cvscreener index` (re)builds the store from `data/profiles/`;
  `cvscreener search "<query>"` is a standalone CLI check independent of the
  agent.

## 3. Chat agent (`cvscreener chat`)

- LangChain tool-calling agent (`ChatOpenAI`, `gpt-4o-mini`) with three tools
  wrapping the vector store: `semantic_search(query)`,
  `filter_search(field, value)`, `get_candidate_profile(name)`. The agent
  never receives the full dataset in its prompt — only tool results.
- System prompt: always search before answering, cite candidates by name,
  and explicitly say "no matching candidate" when a search/filter returns
  nothing — no fabrication.
- Plain CLI REPL loop (`while True: input()`), per the task's CLI-only
  requirement.

## 4. Evals and tests

- `evals/cases.yaml`: ≥5 cases mirroring the task's example questions
  (Python experience, Spanish speakers, best-fit senior ML role, summarize a
  named candidate, plus a deliberate no-match query). `run_evals.py` runs
  each through the agent, checks expected candidate names appear in the
  answer/tool output, prints per-case pass/fail and a final tally. Result is
  pasted into `NOTES.md` as-is, no cherry-picking.
- `tests/`: ≥2 tests runnable with zero API key and zero running database —
  profile schema validation, PDF rendering (mocking the prose/photo
  generation calls), and filter/query-builder logic in `indexing/filters.py`.
  Any OpenAI calls in the code path under test are stubbed with
  `unittest.mock`.

## 5. Supporting files

- `README.md`: from-scratch setup in English — `docker compose up -d`,
  `poetry install`, `.env` from `.env.example`, then `generate` / `index` /
  `chat`.
- `.env.example`: `OPENAI_API_KEY=`, `DATABASE_URL=` (with the compose
  default pre-filled as a comment).
- `NOTES.md`: what's incomplete/broken, the pasted eval run output, next
  steps.
- `CLAUDE.md`: project conventions for future Claude Code sessions.
- Meaningful, incremental English commits as the build progresses
  (`git init` is the first step — this isn't a repo yet).

## Dependencies (new/changed vs. the Chroma version)

- Add: `psycopg[binary]`, `pgvector`, `sqlalchemy`, `langchain-postgres`
- Drop: `chromadb`, `langchain-chroma`
- Unchanged: `langchain`, `langchain-openai`, `openai`, `fpdf2`, `faker`,
  `pydantic`, `typer`, `pytest`, `pyyaml`

## Trade-off note

pgvector needs Postgres running (via Docker Compose) before `index`/`search`/
`chat` will work — Chroma's advantage was zero infra. This is called out in
the README as an explicit prerequisite step, and `filters.py` is kept
DB-free specifically so the "tests pass without an API key" requirement
doesn't also end up implicitly requiring a live database.

## Build order

1. `git init`, scaffold package + pyproject dependencies
2. `docker-compose.yml`, `db.py`, `schemas.py`
3. `generation/` (profiles → prose → photo → PDF), wire into `cvscreener generate`
4. `indexing/` (vectorstore, filters, build_index, search), wire into `cvscreener index` / `search`
5. `agent/` (tools, chat_agent), wire into `cvscreener chat`
6. `evals/cases.yaml` + `run_evals.py`
7. `tests/`
8. `README.md`, `.env.example`, `NOTES.md`, `CLAUDE.md`, `.gitignore`
