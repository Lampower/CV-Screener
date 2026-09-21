"""LangChain tools the chat agent uses to look up candidates.

The agent never receives the dataset in its prompt — these are the only way
it learns anything about candidates, and every tool result is plain text
built from what the search/DB layer actually returned (see
`indexing/search.py`), so answers are traceable back to real data.
"""

from __future__ import annotations

from langchain_core.tools import tool

from cv_screener.indexing.build_index import load_profiles
from cv_screener.indexing.filters import FILTERABLE_FIELDS
from cv_screener.indexing.search import SearchResult, filter_search, semantic_search


def _format_results(results: list[SearchResult]) -> str:
    if not results:
        return "No matching candidates found in the dataset."
    lines = []
    for r in results:
        score_part = f" (similarity distance: {r.score:.3f})" if r.score is not None else ""
        lines.append(f"- {r.full_name} [{r.id}] — {r.role}, {r.seniority}{score_part}\n  {r.snippet}")
    return "\n".join(lines)


@tool
def semantic_search_tool(query: str, k: int = 5) -> str:
    """Search candidates by meaning/context using semantic (vector) search.
    Use this for open-ended or fuzzy questions, e.g. "best fit for a senior
    ML role" or "someone with leadership experience in fintech". `query`
    should be a natural-language description of what you're looking for.
    Returns up to `k` matching candidates with name, role, and a snippet."""
    results = semantic_search(query, k=k)
    return _format_results(results)


@tool
def filter_search_tool(field: str, value: str) -> str:
    """Search candidates by an exact structured field. Use this for concrete
    lookups like a specific language, role, seniority level, location,
    skill, or company. Valid `field` values: full_name, role, seniority,
    location, skills, languages, companies, years_of_experience (supports
    "5", ">=5", ">5", "<=5", "<5" for years_of_experience). `value` is what
    to match, e.g. field="languages", value="Spanish"."""
    if field not in FILTERABLE_FIELDS:
        return (
            f"Invalid field {field!r}. Valid fields are: "
            f"{', '.join(sorted(FILTERABLE_FIELDS))}"
        )
    results = filter_search(field, value)
    return _format_results(results)


@tool
def get_candidate_profile_tool(name: str) -> str:
    """Get the full profile of one candidate by name (exact or partial,
    case-insensitive) — summary, full work experience with highlights,
    education, skills, and languages. Use this to answer "summarize the
    profile of <name>" style questions, or to get full detail on a
    candidate already found via search."""
    name_lower = name.strip().lower()
    matches = [p for p in load_profiles() if name_lower in p.full_name.lower()]
    if not matches:
        return f"No candidate named {name!r} found in the dataset."
    if len(matches) > 1:
        names = ", ".join(p.full_name for p in matches)
        return f"Multiple candidates match {name!r}: {names}. Please specify which one."

    p = matches[0]
    exp_lines = [
        f"  - {e.title} at {e.company} ({e.duration_label}): {'; '.join(e.highlights)}"
        for e in reversed(p.experience)
    ]
    edu_lines = [
        f"  - {e.degree}, {e.institution} ({e.graduation_year})"
        for e in p.education
    ]
    return (
        f"{p.full_name} — {p.role}, {p.seniority} ({p.years_of_experience} years experience)\n"
        f"Location: {p.location}\n"
        f"Summary: {p.summary}\n"
        f"Experience:\n" + ("\n".join(exp_lines) or "  (none)") + "\n"
        f"Education:\n" + ("\n".join(edu_lines) or "  (none)") + "\n"
        f"Skills: {', '.join(p.skills)}\n"
        f"Languages: {', '.join(p.languages)}"
    )


TOOLS = [semantic_search_tool, filter_search_tool, get_candidate_profile_tool]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
