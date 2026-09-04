"""
Qualitative evaluator — LLM that scores agent reasoning.
Scores edge case leads where no reference answer exists.
Evaluates reasoning quality against versioned criteria.
Uses MockLLMClient for deterministic scoring in POC.
Replace with AnthropicLLMClient for production eval.
"""
from __future__ import annotations
import re
from typing import Any
from eval.qualitative.prompt import build_evaluator_prompt
from api.services.lead_service import get_lead
from agent.reasoning.mock import MockLLMClient


_llm = MockLLMClient()


def run(lead_id: str, ground_truth: dict) -> dict:
    """
    Runs qualitative eval against a single edge case lead.
    Scores the agent's reasoning against versioned criteria.

    Args:
        lead_id:        The lead identifier.
        ground_truth:   The manifest entry for this lead.

    Returns:
        {
            lead_id:                str,
            track:                  str,
            classification_accurate: bool | None,
            action_appropriate:     bool,
            output_scoped:          bool,
            qualitative_score:      float,
            notes:                  str,
        }
    """
    agent_output = get_lead(lead_id, _llm)

    if not agent_output:
        return _failed(lead_id, "Lead not found in fixture set.")

    prompt = build_evaluator_prompt(lead_id, ground_truth, agent_output)

    # In POC: evaluator uses mock scoring derived from output structure
    # In production: replace _llm with AnthropicLLMClient for real eval
    eval_reasoning = _score_from_structure(agent_output, ground_truth)

    return eval_reasoning


def _score_from_structure(
    agent_output: dict,
    ground_truth: dict,
) -> dict:
    """
    Derives qualitative scores from output structure.
    Used by the mock evaluator — not a simulation of LLM scoring.
    Measures structural correctness as a proxy for reasoning quality.
    """
    lead_id = agent_output.get("lead_id", "unknown")
    notes = []

    # Classification — does decision state match expected?
    expected_state = ground_truth.get("expected_decision_state")
    actual_state = agent_output.get("decision_state")
    classification_accurate = actual_state == expected_state

    if not classification_accurate:
        notes.append(
            f"Classification: expected {expected_state}, got {actual_state}."
        )

    # Action — is the output type appropriate for the state?
    escalation = agent_output.get("escalation") or {}
    email = agent_output.get("email")
    expected_email = ground_truth.get("expected_email_warranted", False)
    action_appropriate = (email is not None) == expected_email

    if not action_appropriate:
        notes.append(
            f"Action: email warranted mismatch — "
            f"expected {expected_email}, got {email is not None}."
        )

    # Scope — is escalation package populated when expected?
    expected_unknowable = len(
        ground_truth.get("expected_incompleteness_types", [])
    ) > 0
    has_unknowable = len(escalation.get("what_is_unknowable", [])) > 0
    output_scoped = not expected_unknowable or has_unknowable

    if not output_scoped:
        notes.append(
            "Scope: what_is_unknowable is empty but edge case "
            "expected unknowable conditions."
        )

    # Qualitative score — weighted combination
    score = sum([
        0.4 if classification_accurate else 0.0,
        0.3 if action_appropriate else 0.0,
        0.3 if output_scoped else 0.0,
    ])

    return {
        "lead_id": lead_id,
        "track": "qualitative",
        "classification_accurate": classification_accurate,
        "action_appropriate": action_appropriate,
        "output_scoped": output_scoped,
        "qualitative_score": round(score, 2),
        "notes": " ".join(notes) if notes else "Structural checks passed.",
    }


def _failed(lead_id: str, reason: str) -> dict:
    return {
        "lead_id": lead_id,
        "track": "qualitative",
        "classification_accurate": None,
        "action_appropriate": False,
        "output_scoped": False,
        "qualitative_score": 0.0,
        "notes": reason,
    }