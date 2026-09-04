"""
Deterministic eval track — scores clean cases against manifest ground truth.
Checks agent output against known correct values.
No LLM. Rule-based checks only.

Scores three dimensions per lead:
    classification_accurate — did the agent correctly classify incompleteness?
    action_appropriate      — did the agent take the right action?
    output_scoped           — did the agent ask for only what was needed?
"""
from __future__ import annotations
from typing import Any
from api.services.lead_service import get_lead
from agent.reasoning.mock import MockLLMClient


_llm = MockLLMClient()


def run(lead_id: str, ground_truth: dict) -> dict:
    """
    Runs deterministic checks against a single clean lead.
    Compares agent output to manifest ground truth.

    Args:
        lead_id:        The lead identifier.
        ground_truth:   The manifest entry for this lead.

    Returns:
        {
            lead_id:                str,
            track:                  str,
            classification_accurate: bool,
            action_appropriate:     bool,
            output_scoped:          bool,
            qualitative_score:      None,
            notes:                  str,
        }
    """
    result = get_lead(lead_id, _llm)

    if not result:
        return _failed(lead_id, "Lead not found in fixture set.")

    notes = []

    # Check 1 — decision state matches ground truth
    expected_state = ground_truth.get("expected_decision_state")
    actual_state = result.get("decision_state")
    state_correct = actual_state == expected_state

    if not state_correct:
        notes.append(
            f"Decision state mismatch: expected {expected_state}, "
            f"got {actual_state}."
        )

    # Check 2 — hard stops match ground truth
    expected_stops = set(ground_truth.get("expected_hard_stops", []))
    actual_escalation = result.get("escalation") or {}
    actual_stops = {
        s.get("field")
        for s in actual_escalation.get("hard_stops", [])
    }
    stops_correct = expected_stops == actual_stops

    if not stops_correct:
        notes.append(
            f"Hard stop mismatch: expected {expected_stops}, "
            f"got {actual_stops}."
        )

    # Check 3 — email warranted matches ground truth
    expected_email = ground_truth.get("expected_email_warranted", False)
    actual_email = result.get("email") is not None
    email_correct = actual_email == expected_email

    if not email_correct:
        notes.append(
            f"Email warranted mismatch: expected {expected_email}, "
            f"got {actual_email}."
        )

    # Check 4 — mitigation conditions present when expected
    expected_mitigation = ground_truth.get("expected_mitigation_conditions", [])
    actual_mitigation = actual_escalation.get("mitigation_conditions", [])
    mitigation_correct = (
        len(expected_mitigation) == 0
        or len(actual_mitigation) > 0
    )

    if not mitigation_correct:
        notes.append(
            f"Mitigation conditions missing: expected "
            f"{len(expected_mitigation)} conditions, got 0."
        )

    classification_accurate = state_correct and stops_correct
    action_appropriate = state_correct and email_correct
    output_scoped = email_correct and mitigation_correct

    return {
        "lead_id": lead_id,
        "track": "deterministic",
        "classification_accurate": classification_accurate,
        "action_appropriate": action_appropriate,
        "output_scoped": output_scoped,
        "qualitative_score": None,
        "notes": " ".join(notes) if notes else "All checks passed.",
    }


def _failed(lead_id: str, reason: str) -> dict:
    return {
        "lead_id": lead_id,
        "track": "deterministic",
        "classification_accurate": False,
        "action_appropriate": False,
        "output_scoped": False,
        "qualitative_score": None,
        "notes": reason,
    }