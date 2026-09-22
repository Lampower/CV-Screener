"""SQLAlchemy models for the structured-fields table.

Kept separate from `db.py` (connection/engine/session helpers) so that
modules like `indexing/filters.py` can import `CandidateRow` to build
query expressions without pulling in any connection-opening code.
"""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
