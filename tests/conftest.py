"""Shared pytest fixtures. No API key or database required for anything here."""

from __future__ import annotations

import pytest

from cv_screener.schemas import CandidateProfile, Education, Experience


@pytest.fixture
def sample_profile() -> CandidateProfile:
    return CandidateProfile(
        id="test1234",
        full_name="Jane Doe",
        role="Backend Engineer",
        seniority="senior",
        years_of_experience=7,
        location="Berlin, Germany",
        email="jane.doe@example.com",
        phone="+49 30 1234567",
        skills=["Python", "Django", "PostgreSQL", "Docker", "Kafka"],
        languages=["English", "German", "Spanish"],
        education=[
            Education(
                degree="B.Sc. Computer Science",
                field="Computer Science",
                institution="TU Munich",
                graduation_year=2015,
            )
        ],
        experience=[
            Experience(
                title="Senior Backend Engineer",
                company="Nimbusly",
                start_year=2020,
                end_year=None,
                highlights=[
                    "Designed REST APIs serving 50k+ daily requests",
                    "Led on-call rotation and incident response",
                ],
            ),
            Experience(
                title="Backend Engineer",
                company="Fernhollow Labs",
                start_year=2017,
                end_year=2020,
                highlights=["Migrated a monolith service to microservices"],
            ),
        ],
        summary=(
            "Senior backend engineer with 7 years of experience building "
            "scalable APIs and distributed systems."
        ),
    )
