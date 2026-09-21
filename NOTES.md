# Notes

## Object storage (added after the initial build)

Generated photos and PDF resumes now live in S3-compatible object storage
(`storage.py`) instead of local disk. This was added because `minio/minio`
stopped publishing free Docker images in October 2025 and archived the
repo in 2026, so `docker-compose.yml` runs **`pgsty/minio`**, the
community-maintained fork ([pgsty/silo on GitHub](https://github.com/pgsty/silo))
— same server binary, same S3 API, same `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`
env vars, just a Docker Hub account that still ships free images. The app
only ever talks to it through the standard S3 API via `boto3`, so nothing
in `storage.py` is MinIO-specific.

- `cvscreener generate` now uploads photos/PDFs straight to storage — no
  local `data/photos/`/`data/resumes/` files are written for new candidates.
- `cvscreener migrate-storage` is a one-time command that moved this
  project's existing local files (48 files: 24 photos + 24 PDFs, across two
  generation batches) into storage, updated each profile JSON's
  `photo_path`/`resume_pdf_path` to the new object key, and removed the
  local originals once each upload was verified. Confirmed via a direct
  `list_objects_v2` count (48 objects) before deleting locally.
- `data/profiles/*.json` (structured fields) intentionally stayed on local
  disk — only the binary assets moved, per the request.
- Browse the bucket directly at the MinIO console: http://localhost:9001
  (credentials in `.env.example`).

**Dataset note:** between the initial build and this addition, the local
`data/profiles/` directory ended up with 24 candidates instead of 12 (an
extra unseeded `generate --n 12` run happened outside this session, on top
of the original `--seed 7` batch, without clearing first). All 24 were
carried through the storage migration; nothing was deliberately duplicated
or discarded. `evals/cases.yaml`'s `expect_not_contains` assertions were
written to stay valid regardless of how many candidates exist, so this
didn't require rewriting the eval cases.

## Eval run result (as-run, not cherry-picked)

Command: `poetry run python evals/run_evals.py`, against the current
24-candidate dataset, after the storage migration and reindex:

```
========================================================================
[PASS] python_experience
[PASS] spanish_speakers
[PASS] best_fit_senior_ml
[PASS] summarize_named_candidate
[PASS] no_match_query
[PASS] devops_role_filter
========================================================================
RESULT: 6/6 passed
```

**Earlier run, for the record (not deleted just because it later passed):**
against the original 12-candidate (`--seed 7`) dataset, `best_fit_senior_ml`
failed once with "No candidates in the dataset match the criteria for a
senior ML role" instead of naming the dataset's only (junior) ML engineer
as the closest fit — both answers are grounded and non-hallucinating, "best
fit" is inherently a judgment call, and the case wasn't loosened or rerun
to force a pass at the time. With the larger 24-candidate dataset the model
consistently named a closest fit instead, but the case remains a soft spot:
it depends on the model choosing to answer a fuzzy question with "closest
available match" phrasing rather than a strict yes/no.

## Cost

Actual API usage for the full build + eval runs, across both generation
batches (24 candidates total) and two eval runs:

- 24x `gpt-4o-mini` summary calls (~150-250 output tokens each) + 24x
  `gpt-image-1` headshots at `quality="low"`, 1024x1024 (~$0.01-0.02/image)
  + 24x `text-embedding-3-small` calls during indexing.
- Manual smoke-testing of the chat agent (~5 exploratory questions) + two
  full `evals/run_evals.py` runs (6 questions each, 1-2 tool-calling rounds).
- Object storage (`pgsty/minio`) and Postgres (`pgvector`) are self-hosted
  via Docker — zero API cost.
- Rough total: still well under $1-2 of the $2-5 budget. The dominant cost
  is the images; text generation and embeddings are near-free at this scale.

## What's not done / known limitations

- **Headshot realism**: `gpt-image-1` at the `low` quality tier keeps cost
  down (~$0.01-0.02/image instead of ~$0.04-0.17 at `medium`/`high`) but the
  photos are recognizably AI-generated on close inspection rather than
  indistinguishable from real corporate headshots. Bumping `quality` in
  `generation/photos.py` trades budget for realism.
- **Role diversity has some repeats**: 24 candidates span 9 distinct roles
  (Mobile Engineer, QA Engineer, and Engineering Manager each appear more
  than once), though seniority, company, education, and language always
  differ within a repeated role. A bigger role pool in
  `generation/pools.py` would push role uniqueness higher at this `--n`.
- **`migrate-storage` uses a heuristic, not a stored flag**: it decides
  whether a profile's `photo_path`/`resume_pdf_path` is "still local" by
  checking `Path(...).is_absolute()`, since pre-migration paths were
  absolute Windows paths and object keys (`photos/{id}.png`) are always
  relative. This is reliable for this project's history but isn't a
  general-purpose migration marker — a schema version field would be more
  robust if this pattern repeats.
- **No retry/backoff on OpenAI API calls**: `generate` and `chat` call the
  API directly with no retry wrapper. A transient network error mid-`generate`
  run currently just crashes that candidate's turn rather than retrying.
- **No CI/lint config**: no ruff/flake8/mypy wired up. Code follows a
  consistent style but nothing enforces it automatically.
- **`--n` below ~3 can produce thin diversity**: the role/company/university
  pools are large enough for 10-20 candidates to look genuinely distinct;
  very small `--n` runs increase the odds of near-duplicate combinations.

## What I'd do next with more time

1. Add retry/backoff (e.g. `tenacity`, already a transitive dependency via
   `langchain`) around the OpenAI calls in `generate` so a flaky network
   doesn't waste already-spent budget on a partial run.
2. Make the "best fit" style eval cases scored by an LLM-judge rubric
   instead of exact-substring matching, so fuzzy questions aren't
   pass/fail on a single expected name.
3. Bump headshot `quality` to `medium` for a smaller, curated batch (e.g.
   the first 3-4 candidates) as a "hero" set, keeping `low` for the rest —
   better realism where it's most visible without blowing the budget.
4. Add a `--dry-run` / cost-estimate flag to `generate` that prints the
   expected number of API calls before spending anything.
5. Optional (explicitly out of scope per the task): a thin FastAPI wrapper
   over `indexing/search.py` and `agent/chat_agent.py` for a web demo.
6. Serve resume PDFs to end users via `storage.presigned_url()` (already
   implemented, just unused) instead of raw object keys, if this ever
   grows a UI that links out to a candidate's resume.
