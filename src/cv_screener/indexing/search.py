"""Search over the indexed dataset: by structured field, by meaning, or both.

- `semantic_search`: embeds the query, ranks candidates by pgvector cosine
  distance. Used for "who fits X" style questions.
- `filter_search`: exact/fuzzy structured-field lookup against the
  `candidates` SQL table (e.g. languages contains "Spanish"). No embedding
  call, so it's free and instant.
- `hybrid_search`: filters first (SQL), then ranks the surviving candidates
  by semantic similarity to the query — "senior candidates who know Python,
  best fit for an ML role" style questions.
"""

from __future__ import annotations

from dataclasses import dataclass

from cv_screener import db
from cv_screener.indexing.filters import build_filter
from cv_screener.indexing.vectorstore import get_vectorstore


@dataclass
class SearchResult:
    id: str
    full_name: str
    role: str
    seniority: str
    score: float | None  # cosine distance; lower = more similar. None for pure field search.
    snippet: str
    resume_pdf_path: str | None


def semantic_search(query: str, k: int = 5) -> list[SearchResult]:
    vectorstore = get_vectorstore()
    docs_with_scores = vectorstore.similarity_search_with_score(query, k=k)
    results = []
    for doc, score in docs_with_scores:
        md = doc.metadata
        results.append(
            SearchResult(
                id=md.get("id"),
                full_name=md.get("full_name"),
                role=md.get("role"),
                seniority=md.get("seniority"),
                score=float(score),
                snippet=doc.page_content[:500],
                resume_pdf_path=md.get("resume_pdf_path"),
            )
        )
    return results


def filter_search(field: str, value: str, k: int = 20) -> list[SearchResult]:
    condition = build_filter(field, value)
    with db.get_session() as session:
        rows = session.query(db.CandidateRow).filter(condition).limit(k).all()
        return [
            SearchResult(
                id=r.id,
                full_name=r.full_name,
                role=r.role,
                seniority=r.seniority,
                score=None,
                snippet=(
                    f"{r.role} ({r.seniority}), {r.years_of_experience} yrs exp, "
                    f"{r.location}. Skills: {', '.join(r.skills)}. "
                    f"Languages: {', '.join(r.languages)}."
                ),
                resume_pdf_path=r.resume_pdf_path,
            )
            for r in rows
        ]


def hybrid_search(
    query: str, field: str | None = None, value: str | None = None, k: int = 5
) -> list[SearchResult]:
    if not field or not value:
        return semantic_search(query, k=k)

    condition = build_filter(field, value)
    with db.get_session() as session:
        matching_ids = {row.id for row in session.query(db.CandidateRow.id).filter(condition).all()}
    if not matching_ids:
        return []

    ranked = semantic_search(query, k=max(k * 4, 20))
    filtered = [r for r in ranked if r.id in matching_ids]
    return filtered[:k]


def get_by_name(name: str) -> SearchResult | None:
    with db.get_session() as session:
        row = (
            session.query(db.CandidateRow)
            .filter(db.CandidateRow.full_name.ilike(f"%{name}%"))
            .first()
        )
    if not row:
        return None
    return SearchResult(
        id=row.id,
        full_name=row.full_name,
        role=row.role,
        seniority=row.seniority,
        score=None,
        snippet=(
            f"{row.role} ({row.seniority}), {row.years_of_experience} yrs exp, "
            f"{row.location}. Skills: {', '.join(row.skills)}. "
            f"Languages: {', '.join(row.languages)}."
        ),
        resume_pdf_path=row.resume_pdf_path,
    )
