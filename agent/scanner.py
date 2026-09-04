"""
Scanner — first layer of the agent pipeline.
Runs hard stops before any other reasoning.
No LLM. No playbook traversal. Deterministic only.

If hard stops are found the pipeline does not proceed.
The lead routes directly to decline with the scanner findings.

Imports from shared.playbook.hard_stops — does not own the rules.
"""
from __future__ import annotations
from typing import Any
from shared.ontology import (
    DecisionState,
    EscalationPackage,
    LeadState,
)
from shared.playbook.hard_stops import scan


def run(lead_id: str, fields: dict[str, Any]) -> LeadState:
    """
    Runs hard stop detection against a lead's fields.
    Returns a LeadState.

    If hard stops are found:
        - decision_state is DECLINE
        - escalation package contains the findings
        - pipeline stops here

    If no hard stops:
        - decision_state is REFER (placeholder — traverser will resolve)
        - escalation is None
        - pipeline continues to traverser
    """
    hard_stops = scan(fields)

    if hard_stops:
        return LeadState(
            lead_id=lead_id,
            decision_state=DecisionState.DECLINE,
            escalation=EscalationPackage(
                lead_id=lead_id,
                decision_state=DecisionState.DECLINE,
                hard_stops=hard_stops,
                triage_results=[],
                what_is_known=[
                    f"{s.field_name}: {s.reason}"
                    for s in hard_stops
                ],
                what_is_unknowable=[],
                underwriter_decision_required="",
                mitigation_conditions=[],
            ),
            email_warranted=False,
            email_target_fields=[],
        )

    # No hard stops — pipeline continues
    return LeadState(
        lead_id=lead_id,
        decision_state=DecisionState.REFER,  # traverser will resolve
        escalation=None,
        email_warranted=False,
        email_target_fields=[],
    )