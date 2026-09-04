"""
Analyzer — surfaces patterns across eval runs.
The embryonic form of the portfolio-level pattern detector.
In POC: identifies which failure modes are recurring.
In production: monitors proxy drift and emerging unknown unknowns.
"""
from __future__ import annotations
from eval.results.store import get_results


def get_patterns() -> dict:
    """
    Analyzes stored eval results for recurring patterns.
    Returns a structured summary of where agent reasoning is thin.

    Returns:
        {
            most_common_failures:   list[dict],
            classification_accuracy: float,
            action_accuracy:        float,
            scope_accuracy:         float,
            leads_needing_attention: list[str],
        }
    """
    results = get_results()

    if not results:
        return {
            "most_common_failures": [],
            "classification_accuracy": 0.0,
            "action_accuracy": 0.0,
            "scope_accuracy": 0.0,
            "leads_needing_attention": [],
        }

    total = len(results)

    classification_passes = sum(
        1 for r in results
        if r.get("classification_accurate") is True
    )
    action_passes = sum(
        1 for r in results
        if r.get("action_appropriate") is True
    )
    scope_passes = sum(
        1 for r in results
        if r.get("output_scoped") is True
    )

    # Leads that failed on any dimension
    needs_attention = [
        r["lead_id"] for r in results
        if not r.get("action_appropriate")
        or not r.get("output_scoped")
    ]

    # Failure notes as the pattern signal
    failure_notes = [
        {"lead_id": r["lead_id"], "note": r.get("notes", "")}
        for r in results
        if r.get("notes") and r.get("notes") != "All checks passed."
        and r.get("notes") != "Structural checks passed."
    ]

    return {
        "most_common_failures": failure_notes,
        "classification_accuracy": round(classification_passes / total, 2),
        "action_accuracy": round(action_passes / total, 2),
        "scope_accuracy": round(scope_passes / total, 2),
        "leads_needing_attention": needs_attention,
    }