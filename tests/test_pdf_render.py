"""Tests for PDF rendering — pure fpdf2 layout logic, no API key, no DB."""

from __future__ import annotations

from pathlib import Path

from cv_screener.generation.pdf_render import _s, render_resume
from cv_screener.schemas import CandidateProfile


def test_render_resume_writes_a_pdf(sample_profile: CandidateProfile, tmp_path: Path) -> None:
    out_path = tmp_path / "resume.pdf"
    result = render_resume(sample_profile, out_path)
    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 500
    assert out_path.read_bytes().startswith(b"%PDF")


def test_render_resume_without_photo_or_education(tmp_path: Path) -> None:
    minimal = CandidateProfile(
        id="min0001",
        full_name="Alex Smith",
        role="QA Engineer",
        seniority="junior",
        years_of_experience=0,
        location="Remote",
        email="alex.smith@example.com",
        phone="+1 555 0100",
        skills=["Selenium"],
        languages=["English"],
        education=[],
        experience=[],
        summary="Recent graduate eager to start a career in QA.",
    )
    out_path = tmp_path / "minimal.pdf"
    render_resume(minimal, out_path)
    assert out_path.exists()
    assert out_path.stat().st_size > 200


def test_sanitize_replaces_unicode_punctuation_outside_latin1() -> None:
    text = "Senior Engineer — led a team’s roadmap…"
    sanitized = _s(text)
    # must be fully encodable in the Latin-1 core-font charset
    sanitized.encode("latin-1")
    assert "—" not in sanitized
    assert "’" not in sanitized
    assert "…" not in sanitized
