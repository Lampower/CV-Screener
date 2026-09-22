# CLAUDE.md

Guidance for Claude Code (or any future agent) working in this repo.

## What this is

A CV-screening test-task project: generates synthetic candidate resumes
(PDF + photo + structured JSON), indexes them into Postgres/pgvector for
field + semantic search, and answers questions about the dataset via a
CLI tool-calling chat agent. Photos and PDF resumes live in S3-compatible
object storage, not local disk. See `README.md` for setup/run instructions
and `PLAN.md` for the original design rationale.

## Stack

- Python 3.11 (see the Python-version note in `README.md` — 3.14 breaks the
  `numpy` build that `langchain-postgres` pins to `<2.0`)
- Poetry for dependency management, `src/` layout (`src/cv_screener/`)
- Typer CLI (`cv_screener.cli:app`, entry point `cvscreener`)
- OpenAI only: `gpt-4o-mini` (prose + agent), `gpt-image-1` (headshots),
  `text-embedding-3-small` (embeddings)
- Postgres + pgvector via Docker Compose (`docker-compose.yml`), accessed
  through `langchain-postgres` `PGVector` and plain SQLAlchemy
- S3-compatible object storage via the same `docker-compose.yml`, running
  **`pgsty/minio`** (not `minio/minio` — see the "Object storage" note
  below), accessed only through the standard S3 API via `boto3`
  (`storage.py`)

## Conventions

- **Two data stores, deliberately.** `PGVector` (langchain_postgres) holds
  embeddings + a metadata copy for semantic search. A separate
  `CandidateRow` SQL table (model in `models.py`, connection/session
  helpers in `db.py`) holds the same structured fields as real columns,
  used only for field search. Don't try to unify these —
  keeping field search off langchain's internal table schema is what makes
  it simple and version-stable.
- **`indexing/filters.py` must stay DB-free.** It only builds SQLAlchemy
  expressions from `CandidateRow` columns, no connection opened. This is
  what lets `tests/test_filters.py` run with zero infrastructure. If you
  add a new filterable field, add it to `FILTERABLE_FIELDS` and pick the
  right bucket (`SCALAR_FIELDS`/`LIST_FIELDS`/`NUMERIC_FIELDS`).
- **The agent must not see the dataset directly.** `agent/tools.py` /
  `agent/chat_agent.py` only communicate with the model through tool calls
  and their string results. Don't add a "dump all candidates" tool or put
  profile data in the system prompt — that defeats the point being tested.
- **PDF text must survive `_s()` sanitization.** `generation/pdf_render.py`
  uses fpdf2's core Helvetica font, which is Latin-1 only. Any new text
  passed to `pdf.cell`/`multi_cell` needs to go through `_s(...)` first, or
  LLM-written prose with an em dash/curly quote will crash rendering.
- **Money-costing calls are generation and chat/evals only.** `generate`
  calls `gpt-4o-mini` + `gpt-image-1` once each per candidate;
  `index`/`search` cost is just embeddings (cheap); `chat`/`run_evals.py`
  call `gpt-4o-mini` per turn/tool-round. Be mindful of the ~$2-5 budget
  this project was built under — don't add loops that regenerate the whole
  dataset or re-run evals repeatedly without a reason.
- **Tests must run with no API key and no DB.** `tests/` mocks any
  OpenAI/DB-touching call (see `test_agent_tools.py` for the pattern:
  `patch("cv_screener.agent.tools.<name>", ...)`). Keep it that way —
  don't add a test that silently needs `OPENAI_API_KEY` or a live
  `docker compose up` container without marking/skipping it explicitly.
- **Object storage note: `minio/minio` is intentionally not used.** MinIO
  stopped publishing free Docker images in Oct 2025 and archived the repo
  in 2026. `docker-compose.yml` runs `pgsty/minio`
  (https://github.com/pgsty/silo), a community fork with the same server
  binary and env vars. `storage.py` only ever calls the standard S3 API via
  `boto3` — don't add MinIO-SDK-specific code (the `minio` Python package),
  since the whole point is staying swappable to real S3 or another
  S3-compatible backend with just an endpoint/credentials change.
- **Photos/PDFs never touch local disk in `generate`.**
  `generation/photos.py` uploads directly to storage and returns the
  resized image in memory; `generation/pdf_render.py` embeds it and returns
  raw PDF bytes for `cli.py` to upload. Only `data/profiles/*.json`
  (structured fields) is local — keep it that way; don't reintroduce local
  file writes for the binary assets. `cvscreener migrate-storage` exists
  only to backfill datasets generated before storage.py existed; it isn't
  part of the normal `generate` -> `index` -> `chat` flow.

## Common commands

```bash
docker compose up -d                          # start Postgres/pgvector + object storage
poetry install                                # install deps
poetry run cvscreener generate --n 12 --seed 7
poetry run cvscreener migrate-storage         # one-time: only for pre-storage.py datasets
poetry run cvscreener index
poetry run cvscreener search "<query>" [--field F --value V]
poetry run cvscreener chat
poetry run python evals/run_evals.py
poetry run pytest
```

## Commit style

Small, meaningful commits in English, present-tense imperative
("Add pgvector filter search", not "Added" / "Adding"). See git log for
examples.
