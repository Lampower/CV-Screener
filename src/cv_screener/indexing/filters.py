"""Pure filter/query-builder functions for structured-field search.

Nothing in this module opens a database connection or calls an API — it
only builds SQLAlchemy filter expressions (or, for `canonicalize_value`,
does plain string matching against the generation pools). That makes it
unit-testable with zero external dependencies, per the task's "tests run
without an API key" requirement.

`build_filter` is used by `indexing.search.filter_search` to query the
`candidates` table directly.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement

from cv_screener.models import CandidateRow
from cv_screener.generation.pools import (
    COMPANIES,
    LANGUAGE_POOL,
    LOCATIONS,
    ROLES,
    SENIORITY_BANDS,
)

SCALAR_FIELDS = {"full_name", "role", "seniority", "location"}
LIST_FIELDS = {"skills", "languages", "companies"}
NUMERIC_FIELDS = {"years_of_experience"}
FILTERABLE_FIELDS = SCALAR_FIELDS | LIST_FIELDS | NUMERIC_FIELDS

_CANON_POOLS = {
    "role": [r.role for r in ROLES],
    "seniority": SENIORITY_BANDS,
    "location": LOCATIONS,
    "languages": LANGUAGE_POOL,
    "companies": COMPANIES,
    "skills": sorted({s for r in ROLES for s in r.skills}),
}


def canonicalize_value(field: str, raw_value: str) -> str:
    """Best-effort case-insensitive match of `raw_value` against the known
    pool of values for `field` (e.g. "spanish" -> "Spanish"). Falls back to
    `raw_value` unchanged if there's no pool for this field or no match —
    filtering still works via case-insensitive comparison downstream."""
    pool = _CANON_POOLS.get(field)
    if not pool:
        return raw_value
    raw_lower = raw_value.strip().lower()
    for candidate in pool:
        if candidate.lower() == raw_lower:
            return candidate
    # substring fallback, e.g. "ML" -> "ML Engineer"
    for candidate in pool:
        if raw_lower in candidate.lower() or candidate.lower() in raw_lower:
            return candidate
    return raw_value


def build_filter(field: str, value: str) -> ColumnElement:
    """Build a SQLAlchemy filter expression for `CandidateRow.field == value`
    (fuzzy/contains, case-insensitive). Raises ValueError for unknown
    fields so callers (the agent tool) can surface a clear error instead of
    silently matching nothing."""
    if field not in FILTERABLE_FIELDS:
        raise ValueError(
            f"Unknown filterable field {field!r}. Valid fields: "
            f"{', '.join(sorted(FILTERABLE_FIELDS))}"
        )

    column = getattr(CandidateRow, field)

    if field in LIST_FIELDS:
        canon = canonicalize_value(field, value)
        # jsonb array containment: candidates.field @> '["value"]'
        return column.contains([canon])

    if field in NUMERIC_FIELDS:
        # supports "5", ">=5", ">5", "<=5", "<5"
        v = value.strip()
        for op, fn in (
            (">=", column.__ge__), ("<=", column.__le__),
            (">", column.__gt__), ("<", column.__lt__),
        ):
            if v.startswith(op):
                return fn(int(v[len(op):].strip()))
        return column == int(v)

    canon = canonicalize_value(field, value)
    return column.ilike(f"%{canon}%")
