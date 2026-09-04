"""
Escalation composer — formats EscalationPackage for the underwriter.
Produces a structured dict the API serializes and the frontend renders.

The escalation is the primary output for refer and conditionally
bindable leads. It must be precise enough for an underwriter to
act on in ten seconds.

Does not generate prose — structures what the reasoning layer produced.
The underwriter sees this, not the raw EscalationPackage.
"""
from __future__ import annotations
from shared.ontology import EscalationPackage, DecisionState


def compose_escalation(escalation: EscalationPackage) -> dict:
    """
    Formats an EscalationPackage into a structured underwriter-facing dict.

    Returns:
        {
            lead_id:                    str,
            decision_state:             str,
            hard_stops:                 list[dict],
            what_is_known:              list[str],
            what_is_unknowable:         list[str],
            underwriter_decision:       str,
            mitigation_conditions:      list[str],
            triage_summary:             dict,
        }
    """
    triage_summary = _build_triage_summary(escalation)

    return {
        "lead_id": escalation.lead_id,
        "decision_state": escalation.decision_state.value,
        "hard_stops": [
            {
                "field": s.field_name,
                "value": str(s.value),
                "reason": s.reason,
            }
            for s in escalation.hard_stops
        ],
        "what_is_known": escalation.what_is_known,
        "what_is_unknowable": escalation.what_is_unknowable,
        "underwriter_decision": escalation.underwriter_decision_required,
        "mitigation_conditions": escalation.mitigation_conditions,
        "triage_summary": triage_summary,
    }


def _build_triage_summary(escalation: EscalationPackage) -> dict:
    """
    Summarizes triage results by incompleteness type.
    Gives the underwriter a quick read on what kind of problem this is
    before they read the detail.

    Returns:
        {
            auto_fetch:         list[str],  — system will retrieve
            request_via_email:  list[str],  — email warranted
            contradictory:      list[str],  — conflict, no email resolves
            unknowable:         list[str],  — UW judgment required
        }
    """
    from shared.ontology import IncompletenessType

    summary: dict[str, list[str]] = {
        "auto_fetch": [],
        "request_via_email": [],
        "contradictory": [],
        "unknowable": [],
    }

    for result in escalation.triage_results:
        if result.incompleteness_type == IncompletenessType.SYSTEM_OWNED:
            summary["auto_fetch"].append(result.field_name)
        elif result.incompleteness_type == IncompletenessType.ABSENT_RETRIEVABLE:
            summary["request_via_email"].append(result.field_name)
        elif result.incompleteness_type == IncompletenessType.CONTRADICTORY:
            summary["contradictory"].append(result.field_name)
        elif result.incompleteness_type == IncompletenessType.STRUCTURALLY_UNKNOWABLE:
            summary["unknowable"].append(result.field_name)

    return summary