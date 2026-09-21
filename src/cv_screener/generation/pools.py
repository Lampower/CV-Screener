"""Curated pools used to sample diverse, coherent candidates.

The goal is candidates that differ on role, seniority, stack, company,
education, and languages — not ten reskins of the same template. Each role
has its own plausible skill/title/highlight vocabulary so a "Senior ML
Engineer" and a "Junior QA Engineer" don't share a skill list.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class RoleProfile:
    role: str
    titles_by_band: dict[str, str]  # seniority band -> job title
    skills: list[str]
    highlight_templates: list[str]  # {n} years-style filler allowed


SENIORITY_BANDS = ["junior", "mid", "senior", "staff/lead"]

YEARS_RANGE_BY_BAND = {
    "junior": (0, 2),
    "mid": (2, 5),
    "senior": (5, 10),
    "staff/lead": (10, 18),
}

ROLES: list[RoleProfile] = [
    RoleProfile(
        role="Backend Engineer",
        titles_by_band={
            "junior": "Junior Backend Engineer",
            "mid": "Backend Engineer",
            "senior": "Senior Backend Engineer",
            "staff/lead": "Staff Backend Engineer",
        },
        skills=["Python", "Django", "FastAPI", "PostgreSQL", "Redis", "Docker",
                "REST APIs", "Kafka", "gRPC", "Kubernetes", "Go"],
        highlight_templates=[
            "Designed and shipped REST APIs serving {n}k+ daily requests",
            "Migrated a monolith service to a microservices architecture",
            "Reduced p95 API latency by optimizing database queries and caching",
            "Built an internal event-processing pipeline using Kafka",
            "Led on-call rotation and incident response for core services",
        ],
    ),
    RoleProfile(
        role="Frontend Engineer",
        titles_by_band={
            "junior": "Junior Frontend Engineer",
            "mid": "Frontend Engineer",
            "senior": "Senior Frontend Engineer",
            "staff/lead": "Staff Frontend Engineer",
        },
        skills=["JavaScript", "TypeScript", "React", "Next.js", "Vue", "CSS",
                "GraphQL", "Redux", "Webpack", "Accessibility (WCAG)"],
        highlight_templates=[
            "Rebuilt the customer dashboard in React, cutting load time by {n}%",
            "Introduced a component library adopted across {n} product teams",
            "Drove WCAG 2.1 accessibility compliance across the main web app",
            "Implemented CI pipelines for visual regression testing",
            "Mentored junior engineers on modern frontend architecture",
        ],
    ),
    RoleProfile(
        role="ML Engineer",
        titles_by_band={
            "junior": "Junior ML Engineer",
            "mid": "ML Engineer",
            "senior": "Senior ML Engineer",
            "staff/lead": "Staff ML Engineer",
        },
        skills=["Python", "PyTorch", "TensorFlow", "scikit-learn", "MLflow",
                "SQL", "Spark", "LLM fine-tuning", "Vector databases", "AWS SageMaker"],
        highlight_templates=[
            "Trained and deployed a recommendation model improving CTR by {n}%",
            "Built a feature store used by {n} downstream ML models",
            "Fine-tuned open-source LLMs for a domain-specific support chatbot",
            "Owned the model monitoring and drift-detection pipeline",
            "Presented ML roadmap and results to executive leadership",
        ],
    ),
    RoleProfile(
        role="Data Analyst",
        titles_by_band={
            "junior": "Junior Data Analyst",
            "mid": "Data Analyst",
            "senior": "Senior Data Analyst",
            "staff/lead": "Lead Data Analyst",
        },
        skills=["SQL", "Python", "Tableau", "Power BI", "Excel", "dbt",
                "A/B testing", "Statistics", "Looker"],
        highlight_templates=[
            "Built executive dashboards tracking {n}+ core business metrics",
            "Ran A/B tests that informed a {n}% conversion rate improvement",
            "Automated weekly reporting, saving the team {n} hours per week",
            "Partnered with product to define north-star growth metrics",
        ],
    ),
    RoleProfile(
        role="QA Engineer",
        titles_by_band={
            "junior": "Junior QA Engineer",
            "mid": "QA Engineer",
            "senior": "Senior QA Engineer",
            "staff/lead": "QA Lead",
        },
        skills=["Selenium", "Playwright", "pytest", "Postman", "JIRA",
                "Test automation", "Cypress", "Load testing", "CI/CD"],
        highlight_templates=[
            "Built an end-to-end automated regression suite cutting release time by {n}%",
            "Reduced production defect rate by {n}% through improved test coverage",
            "Introduced contract testing between {n} microservices",
            "Owned the release sign-off process across web and mobile",
        ],
    ),
    RoleProfile(
        role="DevOps Engineer",
        titles_by_band={
            "junior": "Junior DevOps Engineer",
            "mid": "DevOps Engineer",
            "senior": "Senior DevOps Engineer",
            "staff/lead": "Staff DevOps / SRE",
        },
        skills=["Terraform", "AWS", "Kubernetes", "Docker", "CI/CD", "Ansible",
                "Prometheus", "Grafana", "GCP", "Linux"],
        highlight_templates=[
            "Migrated infrastructure to Kubernetes, cutting hosting cost by {n}%",
            "Built Terraform modules used across {n} environments",
            "Reduced deployment time from hours to under {n} minutes",
            "Led incident response and built on-call runbooks",
        ],
    ),
    RoleProfile(
        role="Product Manager",
        titles_by_band={
            "junior": "Associate Product Manager",
            "mid": "Product Manager",
            "senior": "Senior Product Manager",
            "staff/lead": "Group Product Manager",
        },
        skills=["Roadmapping", "User research", "SQL", "A/B testing", "Figma",
                "Stakeholder management", "Agile/Scrum", "JIRA"],
        highlight_templates=[
            "Owned the roadmap for a product line generating ${n}M in ARR",
            "Launched a feature adopted by {n}% of the active user base",
            "Ran discovery interviews with {n}+ customers to validate a new product line",
            "Aligned engineering, design, and sales around a quarterly OKR set",
        ],
    ),
    RoleProfile(
        role="UX Designer",
        titles_by_band={
            "junior": "Junior UX Designer",
            "mid": "UX Designer",
            "senior": "Senior UX Designer",
            "staff/lead": "Lead Product Designer",
        },
        skills=["Figma", "User research", "Prototyping", "Design systems",
                "Usability testing", "Sketch", "Adobe XD", "Accessibility"],
        highlight_templates=[
            "Redesigned the onboarding flow, improving activation by {n}%",
            "Built and maintained a design system adopted across {n} products",
            "Ran usability studies with {n}+ participants to guide the redesign",
            "Partnered with PM and engineering on a mobile-first redesign",
        ],
    ),
    RoleProfile(
        role="Security Engineer",
        titles_by_band={
            "junior": "Junior Security Engineer",
            "mid": "Security Engineer",
            "senior": "Senior Security Engineer",
            "staff/lead": "Staff Security Engineer",
        },
        skills=["Penetration testing", "SIEM", "AWS security", "Python",
                "Threat modeling", "OWASP", "Incident response", "IAM"],
        highlight_templates=[
            "Led penetration testing across {n} production services",
            "Built automated detection rules reducing mean time-to-detect by {n}%",
            "Ran the company-wide security awareness and phishing simulation program",
            "Designed the IAM least-privilege model adopted org-wide",
        ],
    ),
    RoleProfile(
        role="Mobile Engineer",
        titles_by_band={
            "junior": "Junior Mobile Engineer",
            "mid": "Mobile Engineer",
            "senior": "Senior Mobile Engineer",
            "staff/lead": "Staff Mobile Engineer",
        },
        skills=["Swift", "Kotlin", "React Native", "iOS", "Android",
                "Firebase", "CI/CD", "GraphQL"],
        highlight_templates=[
            "Shipped a cross-platform app reaching {n}M+ downloads",
            "Cut app crash rate by {n}% through improved error monitoring",
            "Led migration from Objective-C to Swift for the core app",
            "Owned the app release pipeline across iOS and Android",
        ],
    ),
    RoleProfile(
        role="Engineering Manager",
        titles_by_band={
            "junior": "Team Lead",
            "mid": "Engineering Manager",
            "senior": "Senior Engineering Manager",
            "staff/lead": "Director of Engineering",
        },
        skills=["People management", "Roadmapping", "Agile/Scrum", "Hiring",
                "System design", "Cross-team coordination", "Budgeting"],
        highlight_templates=[
            "Grew and managed a team of {n} engineers across two product areas",
            "Led the org through a re-platforming that cut infra costs by {n}%",
            "Owned hiring and onboarding, growing the team from {n} to {n}+ engineers",
            "Partnered with leadership on the annual engineering roadmap",
        ],
    ),
]

COMPANIES = [
    "Nimbusly", "Fernhollow Labs", "Quarrystone Systems", "Brightvale Analytics",
    "Cobalt Ridge Technologies", "Palewind Software", "Kestrel & Finch",
    "Driftwood Digital", "Halcyon Data Co.", "Ironleaf Robotics",
    "Meridian Loop", "Amberfield Health Tech", "Solstice Commerce",
    "Thistledown Studio", "Greycliff Systems", "Northbrook Fintech",
    "Silvergate Cloud", "Wrenfield Media", "Copperline Logistics", "Lucent Path AI",
]

UNIVERSITIES = [
    "University of Toronto", "Technical University of Munich", "UC Berkeley",
    "National University of Singapore", "University of São Paulo",
    "Warsaw University of Technology", "University of Manchester",
    "IIT Bombay", "Seoul National University", "Universidad Politécnica de Madrid",
    "McGill University", "KTH Royal Institute of Technology",
    "University of Cape Town", "Tel Aviv University", "Delft University of Technology",
]

DEGREES_BY_FIELD = {
    "Computer Science": ["B.Sc. Computer Science", "M.Sc. Computer Science"],
    "Data Science": ["B.Sc. Data Science", "M.Sc. Data Science", "M.Sc. Statistics"],
    "Design": ["B.A. Interaction Design", "B.F.A. Design"],
    "Business": ["B.A. Business Administration", "MBA"],
    "Information Systems": ["B.Sc. Information Systems"],
    "Electrical Engineering": ["B.Eng. Electrical Engineering"],
}

LANGUAGE_POOL = [
    "English", "Spanish", "French", "German", "Mandarin", "Portuguese",
    "Japanese", "Korean", "Polish", "Hindi", "Arabic", "Italian", "Russian",
]

LOCATIONS = [
    "Austin, USA", "Berlin, Germany", "Toronto, Canada", "Warsaw, Poland",
    "São Paulo, Brazil", "Singapore", "Amsterdam, Netherlands",
    "Manchester, UK", "Bangalore, India", "Mexico City, Mexico",
    "Lisbon, Portugal", "Seoul, South Korea", "Cape Town, South Africa",
    "Krakow, Poland", "Tel Aviv, Israel",
]


def pick_seniority(rng: random.Random) -> str:
    # weighted a bit toward mid/senior which is realistic for a hiring dataset
    return rng.choices(SENIORITY_BANDS, weights=[0.2, 0.35, 0.3, 0.15])[0]


def pick_role(rng: random.Random) -> RoleProfile:
    return rng.choice(ROLES)


def pick_languages(rng: random.Random) -> list[str]:
    n = rng.choices([1, 2, 3], weights=[0.35, 0.45, 0.2])[0]
    langs = ["English"] if rng.random() < 0.85 else []
    pool = [l for l in LANGUAGE_POOL if l not in langs]
    langs += rng.sample(pool, k=min(n, len(pool)))
    # dedupe, keep order
    seen = set()
    out = []
    for l in langs:
        if l not in seen:
            out.append(l)
            seen.add(l)
    return out
