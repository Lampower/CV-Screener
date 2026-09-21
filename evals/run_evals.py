"""Runs evals/cases.yaml through the real chat agent and prints pass/fail.

Each case is a fresh conversation (no shared history between cases) so
results are independent and reproducible. Requires OPENAI_API_KEY and a
running, indexed Postgres (`docker compose up -d && cvscreener index`).

Usage: `poetry run python evals/run_evals.py` (or `python evals/run_evals.py`
inside an activated venv).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from langchain_core.messages import ToolMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cv_screener import db  # noqa: E402
from cv_screener.agent.chat_agent import build_llm, initial_history, run_turn  # noqa: E402

NO_MATCH_PHRASES = [
    "no candidate", "no one", "none of the candidates", "no match",
    "doesn't match", "does not match", "no results", "nobody",
]

CASES_PATH = Path(__file__).parent / "cases.yaml"


def load_cases() -> list[dict]:
    return yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))


def evaluate_case(llm, case: dict) -> tuple[bool, list[str]]:
    reasons = []
    history = initial_history()
    answer, full_history = run_turn(llm, history, case["question"])
    answer_lower = answer.lower()

    for expected in case.get("expect_contains", []):
        if expected.lower() not in answer_lower:
            reasons.append(f"missing expected mention: {expected!r}")

    for forbidden in case.get("expect_not_contains", []):
        if forbidden.lower() in answer_lower:
            reasons.append(f"unexpected mention (possible hallucination): {forbidden!r}")

    if case.get("expect_no_match"):
        if not any(phrase in answer_lower for phrase in NO_MATCH_PHRASES):
            reasons.append("expected a plain 'no match' answer but didn't find one")

    if case.get("require_tool_call", True):
        called_a_tool = any(isinstance(m, ToolMessage) for m in full_history)
        if not called_a_tool:
            reasons.append("agent answered without calling any tool")

    return (len(reasons) == 0), reasons, answer


def main() -> int:
    if not db.check_connection():
        print("ERROR: cannot connect to Postgres. Run `docker compose up -d` "
              "and `cvscreener index` first.")
        return 2

    cases = load_cases()
    llm = build_llm()

    results = []
    for case in cases:
        passed, reasons, answer = evaluate_case(llm, case)
        results.append((case["id"], passed, reasons, answer))

    print("=" * 72)
    for case_id, passed, reasons, answer in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {case_id}")
        if not passed:
            for r in reasons:
                print(f"    - {r}")
            print(f"    answer: {answer[:300]}")
    print("=" * 72)

    n_passed = sum(1 for _id, passed, _reasons, _answer in results if passed)
    n_total = len(results)
    print(f"RESULT: {n_passed}/{n_total} passed")

    return 0 if n_passed == n_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
