"""Synthetic candidate profile generation.

Structured facts (role, seniority, companies, education, skills, dates) come
from Faker + the curated pools in `pools.py`, sampled so each candidate is a
coherent person rather than random noise. A single `gpt-4o-mini` call per
candidate turns those facts into natural prose (summary + experience
bullets) so the resume reads like a real CV, not a template dump.
"""

from __future__ import annotations

import json
import random
import re
import uuid
from datetime import date

from faker import Faker
from openai import OpenAI

from cv_screener.config import CHAT_MODEL, require_api_key
from cv_screener.generation.pools import (
    COMPANIES,
    DEGREES_BY_FIELD,
    LOCATIONS,
    UNIVERSITIES,
    YEARS_RANGE_BY_BAND,
    pick_languages,
    pick_role,
    pick_seniority,
)
from cv_screener.schemas import CandidateProfile, Education, Experience

CURRENT_YEAR = date.today().year

ROLE_TO_FIELD = {
    "Backend Engineer": "Computer Science",
    "Frontend Engineer": "Computer Science",
    "ML Engineer": "Data Science",
    "Data Analyst": "Data Science",
    "QA Engineer": "Computer Science",
    "DevOps Engineer": "Electrical Engineering",
    "Product Manager": "Business",
    "UX Designer": "Design",
    "Security Engineer": "Computer Science",
    "Mobile Engineer": "Computer Science",
    "Engineering Manager": "Computer Science",
}

NUM_PAST_ROLES_BY_BAND = {
    "junior": (1, 2),
    "mid": (2, 3),
    "senior": (2, 4),
    "staff/lead": (3, 5),
}


def _build_experience(
    rng: random.Random, role_profile, seniority: str, years_of_experience: int
) -> list[Experience]:
    if years_of_experience < 1:
        return []  # fresh graduate, no professional experience yet

    n_roles = rng.randint(*NUM_PAST_ROLES_BY_BAND[seniority])
    n_roles = max(1, min(n_roles, max(1, years_of_experience)))

    start_of_career = CURRENT_YEAR - years_of_experience
    # split career span into n_roles chunks of >=1 year
    boundaries = sorted(
        rng.sample(
            range(start_of_career + 1, CURRENT_YEAR), k=min(n_roles - 1, max(0, CURRENT_YEAR - start_of_career - 1))
        )
    )
    edges = [start_of_career, *boundaries, CURRENT_YEAR]

    companies = rng.sample(COMPANIES, k=min(n_roles, len(COMPANIES)))
    titles_pool = list(role_profile.titles_by_band.values())

    experience = []
    for i in range(len(edges) - 1):
        start, end = edges[i], edges[i + 1]
        is_latest = i == len(edges) - 2
        title = role_profile.titles_by_band[seniority] if is_latest else rng.choice(titles_pool)
        highlights = rng.sample(
            role_profile.highlight_templates,
            k=min(rng.choice([2, 3]), len(role_profile.highlight_templates)),
        )
        filled = [h.format(n=rng.choice([10, 15, 20, 25, 30, 40, 50, 3, 5])) for h in highlights]
        experience.append(
            Experience(
                title=title,
                company=companies[i % len(companies)],
                start_year=start,
                end_year=None if is_latest else end,
                highlights=filled,
            )
        )
    return experience


def _build_education(rng: random.Random, role: str, seniority: str) -> list[Education]:
    field_name = ROLE_TO_FIELD.get(role, "Computer Science")
    degrees = DEGREES_BY_FIELD[field_name]
    grad_year_bachelor = CURRENT_YEAR - rng.randint(4, 10) - (0 if seniority == "junior" else rng.randint(0, 8))
    entries = [
        Education(
            degree=degrees[0],
            field=field_name,
            institution=rng.choice(UNIVERSITIES),
            graduation_year=grad_year_bachelor,
        )
    ]
    has_masters = len(degrees) > 1 and (seniority in ("senior", "staff/lead") or rng.random() < 0.3)
    if has_masters:
        entries.append(
            Education(
                degree=degrees[-1],
                field=field_name,
                institution=rng.choice(UNIVERSITIES),
                graduation_year=grad_year_bachelor + rng.randint(1, 2),
            )
        )
    return entries


def _sample_skeleton(rng: random.Random, faker: Faker) -> CandidateProfile:
    role_profile = pick_role(rng)
    seniority = pick_seniority(rng)
    lo, hi = YEARS_RANGE_BY_BAND[seniority]
    years_of_experience = rng.randint(lo, hi)

    first = faker.first_name()
    last = faker.last_name()
    full_name = f"{first} {last}"
    domain_slug = re.sub(r"[^a-z0-9]", "", rng.choice(COMPANIES).lower())
    company_domain = f"{domain_slug}.example"

    skills = rng.sample(role_profile.skills, k=min(rng.randint(6, 9), len(role_profile.skills)))
    experience = _build_experience(rng, role_profile, seniority, years_of_experience)
    education = _build_education(rng, role_profile.role, seniority)
    languages = pick_languages(rng)

    return CandidateProfile(
        id=str(uuid.uuid4())[:8],
        full_name=full_name,
        role=role_profile.role,
        seniority=seniority,
        years_of_experience=years_of_experience,
        location=rng.choice(LOCATIONS),
        email=f"{first.lower()}.{last.lower()}@{company_domain}",
        phone=faker.phone_number(),
        skills=skills,
        languages=languages,
        education=education,
        experience=experience,
    )


_SUMMARY_SYSTEM_PROMPT = """You write a single professional resume summary \
paragraph (3-4 sentences, first person is NOT used, no "I") given structured \
facts about a candidate. Be specific and grounded in the given facts only \
(role, seniority, years of experience, skills, most recent company, \
education). Do not invent employers, metrics, or skills not given to you. \
Sound like a real CV summary, not a marketing blurb. Return plain text only, \
no markdown, no quotes."""


def _generate_summary(client: OpenAI, profile: CandidateProfile) -> str:
    latest = profile.experience[-1] if profile.experience else None
    facts = {
        "full_name": profile.full_name,
        "role": profile.role,
        "seniority": profile.seniority,
        "years_of_experience": profile.years_of_experience,
        "top_skills": profile.skills[:6],
        "most_recent_title": latest.title if latest else None,
        "most_recent_company": latest.company if latest else None,
        "education": [e.degree for e in profile.education],
        "languages": profile.languages,
    }
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(facts)},
        ],
        max_tokens=220,
        temperature=0.8,
    )
    return resp.choices[0].message.content.strip()


def generate_candidates(n: int, seed: int | None = None) -> list[CandidateProfile]:
    """Generate `n` diverse synthetic candidate profiles with LLM-written
    summaries. Does not render PDFs or photos — see `pdf_render.py` /
    `photos.py`."""
    require_api_key()
    client = OpenAI()
    rng = random.Random(seed)
    faker = Faker()
    if seed is not None:
        Faker.seed(seed)

    candidates: list[CandidateProfile] = []
    seen_names: set[str] = set()
    attempts = 0
    while len(candidates) < n and attempts < n * 5:
        attempts += 1
        profile = _sample_skeleton(rng, faker)
        if profile.full_name in seen_names:
            continue  # keep candidates distinct
        seen_names.add(profile.full_name)
        profile.summary = _generate_summary(client, profile)
        candidates.append(profile)

    return candidates
