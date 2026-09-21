"""Tests for CandidateProfile — pure Pydantic logic, no API key, no DB."""

from __future__ import annotations

from cv_screener.schemas import CandidateProfile


def test_embedding_text_includes_narrative_content(sample_profile: CandidateProfile) -> None:
    text = sample_profile.embedding_text()
    assert sample_profile.full_name in text
    assert sample_profile.summary in text
    assert "Nimbusly" in text
    assert "Python" in text
    assert "Spanish" in text


def test_metadata_has_structured_fields_for_filtering(sample_profile: CandidateProfile) -> None:
    md = sample_profile.metadata()
    assert md["id"] == "test1234"
    assert md["role"] == "Backend Engineer"
    assert md["seniority"] == "senior"
    assert md["years_of_experience"] == 7
    assert "Spanish" in md["languages"]
    assert md["companies"] == ["Nimbusly", "Fernhollow Labs"]


def test_experience_duration_label_handles_current_role(sample_profile: CandidateProfile) -> None:
    current_role = sample_profile.experience[0]
    past_role = sample_profile.experience[1]
    assert current_role.duration_label == "2020-Present"
    assert past_role.duration_label == "2017-2020"


def test_profile_round_trips_through_json(sample_profile: CandidateProfile) -> None:
    dumped = sample_profile.model_dump_json()
    restored = CandidateProfile.model_validate_json(dumped)
    assert restored == sample_profile
