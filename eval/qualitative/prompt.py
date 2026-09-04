"""
Qualitative evaluator prompt — built from versioned criteria.
The evaluator LLM scores agent reasoning against these criteria.
Never scores against a reference answer — scores reasoning quality.
"""
from __future__ import annotations
from eval.qualitative.criteria import (
    VERSION,
    INCOMPLETENESS_CLASSIFICATIONS,
    ACTION_CRITERIA,
    SCOPE_CRITERIA,
    UNKNOWN_UNKNOWNS_CRITERIA,
)


def build_evaluator_prompt(
    lead_id: str,
    ground_truth: dict,
    agent_output: dict,
) -> str:
    """
    Builds the evaluator prompt from criteria and agent output.
    The evaluator scores three dimensions independently.
    Returns a structured prompt string.
    """
    expected_state = ground_truth.get("expected_decision_state")
    expected_types = ground_truth.get("expected_incompleteness_types", [])
    archetype = ground_truth.get("archetype")
    gt_notes = ground_truth.get("notes", "")

    actual_state = agent_output.get("decision_state")
    escalation = agent_output.get("escalation") or {}
    reasoning = agent_output.get("reasoning", "None provided.")
    email = agent_output.get("email")

    known = "\n".join(
        f"- {k}" for k in escalation.get("what_is_known", [])
    ) or "None."

    unknowable = "\n".join(
        f"- {u}" for u in escalation.get("what_is_unknowable", [])
    ) or "None."

    uw_decision = escalation.get("underwriter_decision", "None.")
    mitigation = "\n".join(
        f"- {m}" for m in escalation.get("mitigation_conditions", [])
    ) or "None."

    email_summary = (
        f"Subject: {email.get('subject')}\n"
        f"Target fields: {email.get('metadata', {}).get('target_fields', [])}"
        if email else "No email generated."
    )

    return f"""You are an expert underwriting evaluator scoring an AI
agent's reasoning over a property insurance lead.

You do not score whether the agent got the right answer.
You score the quality of its reasoning — whether it correctly
identified what kind of problem it was dealing with, took the
right action for that problem, and produced output that was
precisely scoped.

CRITERIA VERSION: {VERSION}
LEAD ID: {lead_id}
ARCHETYPE: {archetype}
GROUND TRUTH NOTES: {gt_notes}

EXPECTED DECISION STATE: {expected_state}
ACTUAL DECISION STATE: {actual_state}
EXPECTED INCOMPLETENESS TYPES: {expected_types}

--- AGENT OUTPUT ---

WHAT IS KNOWN:
{known}

WHAT IS UNKNOWABLE:
{unknowable}

UNDERWRITER DECISION REQUIRED:
{uw_decision}

MITIGATION CONDITIONS:
{mitigation}

EMAIL OUTPUT:
{email_summary}

AGENT REASONING:
{reasoning}

--- EVALUATION CRITERIA ---

INCOMPLETENESS CLASSIFICATIONS:
{INCOMPLETENESS_CLASSIFICATIONS}

ACTION CRITERIA:
{ACTION_CRITERIA}

SCOPE CRITERIA:
{SCOPE_CRITERIA}

UNKNOWN UNKNOWNS CRITERIA:
{UNKNOWN_UNKNOWNS_CRITERIA}

--- YOUR TASK ---

Score the agent's output on three dimensions.
For each dimension provide:
    - A score: PASS or FAIL
    - One sentence explaining why

DIMENSION 1 — CLASSIFICATION ACCURATE:
Did the agent correctly identify the type of incompleteness
it was dealing with for this lead?

DIMENSION 2 — ACTION APPROPRIATE:
Did the agent take the right action for its classification?

DIMENSION 3 — OUTPUT SCOPED:
Was the agent's output precisely scoped — did it ask for
only what was needed, surface only what was genuinely
unknowable, and frame the underwriter decision precisely?

BONUS — UNKNOWN UNKNOWNS:
Did the agent surface any signal that goes beyond what the
playbook explicitly encoded? If yes, describe it.

Respond in this exact structure:

CLASSIFICATION: [PASS|FAIL] — [one sentence]
ACTION: [PASS|FAIL] — [one sentence]
SCOPE: [PASS|FAIL] — [one sentence]
UNKNOWN_UNKNOWNS: [YES|NO] — [one sentence]
OVERALL_SCORE: [0.0-1.0]
"""