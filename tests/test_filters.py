"""Tests for indexing/filters.py — pure query-builder functions, no DB connection
opened anywhere in this file (building a SQLAlchemy expression doesn't touch
the network), and no API key needed."""

from __future__ import annotations

import pytest
from sqlalchemy import ColumnElement
from sqlalchemy.dialects import postgresql

from cv_screener.indexing.filters import build_filter, canonicalize_value


def _compile_pg(expr: ColumnElement) -> str:
    """Compile against the Postgres dialect (what actually runs in
    production) rather than the generic dialect, which renders ILIKE/JSONB
    differently or not at all."""
    return str(expr.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_canonicalize_value_matches_case_insensitively() -> None:
    assert canonicalize_value("languages", "spanish") == "Spanish"
    assert canonicalize_value("seniority", "SENIOR") == "senior"


def test_canonicalize_value_falls_back_to_raw_when_no_pool_match() -> None:
    assert canonicalize_value("languages", "Klingon") == "Klingon"


def test_canonicalize_value_no_pool_for_field_returns_raw() -> None:
    assert canonicalize_value("full_name", "Jane Doe") == "Jane Doe"


def test_build_filter_scalar_field_returns_ilike_expression() -> None:
    expr = build_filter("role", "ml engineer")
    assert isinstance(expr, ColumnElement)
    compiled = _compile_pg(expr)
    assert "ILIKE" in compiled.upper()
    assert "ML Engineer" in compiled  # canonicalized from lowercase input


def test_build_filter_list_field_uses_jsonb_contains() -> None:
    expr = build_filter("languages", "spanish")
    compiled = expr.compile(dialect=postgresql.dialect())
    assert "@>" in str(compiled)
    # JSONB literal rendering needs a live DBAPI adapter, so check the bound
    # parameter value directly instead of the literal-inlined SQL string.
    assert ["Spanish"] in compiled.params.values()  # canonicalized


@pytest.mark.parametrize(
    "raw_value,expected_operator",
    [(">=5", ">="), ("<=3", "<="), (">2", ">"), ("<10", "<"), ("5", "=")],
)
def test_build_filter_numeric_field_supports_comparison_operators(
    raw_value: str, expected_operator: str
) -> None:
    expr = build_filter("years_of_experience", raw_value)
    compiled = _compile_pg(expr)
    assert expected_operator in compiled


def test_build_filter_unknown_field_raises_value_error() -> None:
    with pytest.raises(ValueError):
        build_filter("favorite_color", "blue")
