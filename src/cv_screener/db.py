"""Database connection helpers (engine/session/schema init).

Two things live in Postgres, side by side:

1. The `langchain_pg_*` tables owned by `langchain_postgres.PGVector` — the
   embedding vectors plus a copy of each candidate's metadata as jsonb.
   This is the "resumes go into the vector store together with structured
   fields" requirement, and it's what semantic search queries.
2. A plain `candidates` table (model in `models.py`) — the same structured
   fields as normal SQL columns/JSON, owned entirely by this app. Field
   search (`filter_search`) queries this table directly with `WHERE`
   clauses instead of reaching into langchain_postgres' internal schema,
   which keeps field search simple, fast, and independent of that
   library's internal table layout.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from cv_screener.config import DATABASE_URL
from cv_screener.models import Base

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine


def get_session() -> Session:
    return sessionmaker(bind=get_engine())()


def init_schema() -> None:
    """Create the `candidates` table if it doesn't exist yet. Safe to call
    repeatedly. langchain_postgres creates its own tables lazily on first
    use, so it isn't touched here."""
    Base.metadata.create_all(get_engine())


def check_connection() -> bool:
    """Quick liveness check used by the CLI to give a friendly error if the
    `db` docker-compose service isn't up yet."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
