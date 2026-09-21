"""Builds/rebuilds the index from data/profiles/*.json.

Populates two things (see db.py for why there are two):
  1. the `candidates` SQL table — structured fields for field search
  2. the pgvector collection — embedding text + metadata for semantic search
"""

from __future__ import annotations

from cv_screener import db
from cv_screener.config import PROFILES_DIR
from cv_screener.indexing.vectorstore import get_vectorstore
from cv_screener.schemas import CandidateProfile


def load_profiles() -> list[CandidateProfile]:
    profiles = []
    for f in sorted(PROFILES_DIR.glob("*.json")):
        profiles.append(CandidateProfile.model_validate_json(f.read_text(encoding="utf-8")))
    return profiles


def build_index(profiles: list[CandidateProfile] | None = None) -> int:
    if profiles is None:
        profiles = load_profiles()
    if not profiles:
        raise RuntimeError(
            "No candidate profiles found in data/profiles/. Run `cvscreener generate` first."
        )

    db.init_schema()
    with db.get_session() as session:
        session.query(db.CandidateRow).delete()
        for p in profiles:
            session.add(
                db.CandidateRow(
                    id=p.id,
                    full_name=p.full_name,
                    role=p.role,
                    seniority=p.seniority,
                    years_of_experience=p.years_of_experience,
                    location=p.location,
                    skills=p.skills,
                    languages=p.languages,
                    companies=[e.company for e in p.experience],
                    resume_pdf_path=p.resume_pdf_path,
                    photo_path=p.photo_path,
                )
            )
        session.commit()

    vectorstore = get_vectorstore()
    try:
        vectorstore.delete_collection()  # full rebuild, avoid stale duplicates
    except Exception:
        pass
    vectorstore = get_vectorstore()  # re-creates the (now-empty) collection

    texts = [p.embedding_text() for p in profiles]
    metadatas = [p.metadata() for p in profiles]
    ids = [p.id for p in profiles]
    vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    return len(profiles)
