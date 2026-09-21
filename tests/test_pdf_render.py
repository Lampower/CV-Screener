"""Tests for PDF rendering — pure fpdf2 layout logic, no API key, no DB, no
object storage. render_resume() returns raw PDF bytes; nothing touches
local disk or S3 in this module (the CLI is what uploads the result)."""

from __future__ import annotations

from PIL import Image

from cv_screener.generation.pdf_render import _s, render_resume
from cv_screener.schemas import CandidateProfile


def test_render_resume_returns_pdf_bytes(sample_profile: CandidateProfile) -> None:
    result = render_resume(sample_profile)
    assert isinstance(result, bytes)
    assert len(result) > 500
    assert result.startswith(b"%PDF")


def test_render_resume_with_in_memory_photo(sample_profile: CandidateProfile) -> None:
    photo = Image.new("RGB", (100, 100), color=(200, 150, 100))
    result = render_resume(sample_profile, photo=photo)
    assert result.startswith(b"%PDF")
    # embedding a photo should make the PDF meaningfully larger than without one
    assert len(result) > len(render_resume(sample_profile))


def test_render_resume_without_photo_or_education() -> None:
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
    result = render_resume(minimal)
    assert result.startswith(b"%PDF")
    assert len(result) > 200


def test_sanitize_replaces_unicode_punctuation_outside_latin1() -> None:
    text = "Senior Engineer — led a team’s roadmap…"
    sanitized = _s(text)
    # must be fully encodable in the Latin-1 core-font charset
    sanitized.encode("latin-1")
    assert "—" not in sanitized
    assert "’" not in sanitized
    assert "…" not in sanitized
