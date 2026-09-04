"""
Feedback integrator — turns underwriter decisions into eval signal.
The mechanism by which the system compounds.
In POC: logs signal for review.
In production: updates qualitative criteria weights automatically.
"""
from __future__ import annotations
from typing import Any


def integrate(annotated_results: list[dict]) -> dict:
    """
    Analyzes annotated eval results for learning signal.
    Returns a summary of what the underwriter confirmed and corrected.

    In production this would:
    - Update criteria.py weights based on confirmation rate
    - Flag criteria that underwriters consistently disagree with
    - Version the criteria change with a timestamp and rationale

    Args:
        annotated_results: Eval results with underwriter_confirmed set.

    Returns:
        {
            confirmed:          int,
            corrected:          int,
            confirmation_rate:  float,
            corrections:        list[dict],
        }
    """
    confirmed = []
    corrected = []

    for result in annotated_results:
        if "underwriter_confirmed" not in result:
            continue
        if result["underwriter_confirmed"]:
            confirmed.append(result["lead_id"])
        else:
            corrected.append({
                "lead_id": result["lead_id"],
                "agent_classification": result.get("classification_accurate"),
                "underwriter_decision": result.get("underwriter_decision"),
                "underwriter_reasoning": result.get("underwriter_reasoning"),
            })

    total = len(confirmed) + len(corrected)
    confirmation_rate = round(len(confirmed) / total, 2) if total > 0 else 0.0

    return {
        "confirmed": len(confirmed),
        "corrected": len(corrected),
        "confirmation_rate": confirmation_rate,
        "corrections": corrected,
    }