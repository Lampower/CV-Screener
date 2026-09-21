"""Database connection helpers + the structured-fields table.

Two things live in Postgres, side by side:

1. The `langchain_pg_*` tables owned by `langchain_postgres.PGVector` — the
   embedding vectors plus a copy of each candidate's metadata as jsonb.
   This is the "resumes go into the vector store together with structured
   fields" requirement, and it's what semantic search queries.
2. A plain `candidates` table defined here — the same structured fields as
   normal SQL columns/JSON, owned entirely by this app. Field search
   (`filter_search`) queries this table directly with `WHERE` clauses
   instead of reaching into langchain_postgres' internal schema, which
   keeps field search simple, fast, and independent of that library's
   internal table layout.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from cv_screener.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class CandidateRow(Base):
    """Structured fields for one candidate, mirrored from CandidateProfile."""

    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    full_name: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String, index=True)
    seniority: Mapped[str] = mapped_column(String, index=True)
    years_of_experience: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String)
    skills: Mapped[list] = mapped_column(JSONB)
    languages: Mapped[list] = mapped_column(JSONB)
    companies: Mapped[list] = mapped_column(JSONB)
    resume_pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String, nullable=True)


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
