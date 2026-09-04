"""
Traverser — second layer of the agent pipeline.
Walks the encoded playbook pages against the lead fields.
Applies triage rules from shared.triage_rules.
Classifies incompleteness for every missing or conflicting field.
Determines the dominant decision state across all playbook findings.

No LLM. Deterministic traversal only.
The LLM reasoning layer receives the output of this layer —
never the raw lead fields.

Decision state priority (highest to lowest):
    DECLINE > REFER > CONDITIONALLY_BINDABLE > READY_TO_QUOTE

A lead with any decline finding is a decline.
A lead with any refer finding and no decline is a refer.
A lead with only mitigation conditions is conditionally bindable.
A lead with no findings is ready to quote.
"""
from __future__ import annotations
from typing import Any
from shared.ontology import (
    DecisionState,
    EscalationPackage,
    LeadState,
    TriageResult,
    IncompletenessType,
)
from shared.triage_rules import triage_action, is_blocking, classify_incompleteness
from shared.registry import fields as registry_fields, required_level, meta
import shared.playbook.profile as profile_playbook
import shared.playbook.occupancy as occupancy_playbook
import shared.playbook.pc9_10 as pc9_10_playbook


# Decision state priority — higher index wins
STATE_PRIORITY = [
    DecisionState.READY_TO_QUOTE,
    DecisionState.CONDITIONALLY_BINDABLE,
    DecisionState.REFER,
    DecisionState.DECLINE,
]


def run(lead_id: str, fields: dict[str, Any]) -> LeadState:
    """
    Traverses all encoded playbook pages against the lead fields.
    Collects findings across pages.
    Resolves the dominant decision state.
    Returns a LeadState ready for the reasoning layer or composer.
    """
    findings: list[EscalationPackage] = []

    # --- Field-level triage against registry ---
    triage_results = _triage_fields(fields)

    # --- Playbook page traversal ---
    # Pages are evaluated independently.
    # Each returns an EscalationPackage or None if clean.

    profile_finding = profile_playbook.evaluate(lead_id, fields)
    if profile_finding:
        findings.append(profile_finding)

    occupancy_finding = occupancy_playbook.evaluate(lead_id, fields)
    if occupancy_finding:
        findings.append(occupancy_finding)

    pc9_10_finding = pc9_10_playbook.evaluate(lead_id, fields)
    if pc9_10_finding:
        findings.append(pc9_10_finding)

    # --- Resolve dominant decision state ---
    dominant_state = _resolve_dominant_state(findings)

    # --- Build consolidated escalation package ---
    if not findings and not _has_blocking_triage(triage_results):
        # Clean lead — ready to quote
        return LeadState(
            lead_id=lead_id,
            decision_state=DecisionState.READY_TO_QUOTE,
            escalation=None,
            email_warranted=False,
            email_target_fields=[],
        )

    # Consolidate findings into one escalation package
    escalation = _consolidate(lead_id, dominant_state, findings, triage_results)

    # Determine email warranted and target fields
    email_fields = _email_target_fields(triage_results)

    return LeadState(
        lead_id=lead_id,
        decision_state=dominant_state,
        escalation=escalation,
        email_warranted=len(email_fields) > 0,
        email_target_fields=email_fields,
    )


def _triage_fields(fields: dict[str, Any]) -> list[TriageResult]:
    """
    Runs every field in the lead against the registry triage rules.
    Returns a list of TriageResult for fields that need action.
    Skips fields that are present and valid.
    """
    results: list[TriageResult] = []
    reg = registry_fields()

    for field_name, field_meta in reg.items():
        value = fields.get(field_name)

        # Check conditional requirements
        if field_meta.get("required") == "conditional":
            if not _conditional_is_triggered(field_name, field_meta, fields):
                continue

        action = triage_action(field_name, value)

        # Skip fields that are present or optional
        if action in ("present", "optional", "defer_to_bind"):
            continue

        incompleteness = classify_incompleteness(field_name)
        blocking = is_blocking(field_name, value)
        minimum_sufficient = False  # traverser sets this; reasoning layer refines

        results.append(TriageResult(
            field_name=field_name,
            incompleteness_type=incompleteness,
            triage_action=action,
            blocking=blocking,
            minimum_sufficient=minimum_sufficient,
        ))

    return results


def _conditional_is_triggered(
    field_name: str,
    field_meta: dict,
    fields: dict[str, Any],
) -> bool:
    """
    Evaluates whether a conditional field's requiredWhen condition is met.
    Returns True if the field is currently required.
    Encodes the requiredWhen logic from the field registry.
    """
    required_when = field_meta.get("requiredWhen", "")

    if not required_when:
        return False

    # pool_security, pool_has_diving_board_or_slide
    if "pool_type != None" in required_when:
        return fields.get("pool_type") not in (None, "None")

    # above_ground_pool_ladder
    if "pool_type = Above Ground" in required_when:
        return fields.get("pool_type") == "Above Ground"

    # post_pier_supports_living_area, deck_height_ft
    if "foundation_type in (Piers, Stilts, Pilings)" in required_when:
        return fields.get("foundation_type") in ("Piers", "Stilts", "Pilings")

    # trust_name
    if "residence_held_in_trust = true" in required_when:
        return fields.get("residence_held_in_trust") is True

    # water_heater_age_years, water_heater_location
    if "water_heater_type = Tank" in required_when:
        return fields.get("water_heater_type") == "Tank"

    # fire_dept_response_time, alternative_water_source,
    # interior_sprinklers, physical_barriers
    if "protection_class in (9, 10)" in required_when:
        pc = fields.get("protection_class")
        if pc is None:
            pc = "9"  # missingDefault
        return str(pc) in ("9", "10")

    return False


def _resolve_dominant_state(
    findings: list[EscalationPackage],
) -> DecisionState:
    """
    Applies decision state priority across all playbook findings.
    DECLINE > REFER > CONDITIONALLY_BINDABLE > READY_TO_QUOTE
    A single decline finding makes the lead a decline.
    """
    if not findings:
        return DecisionState.READY_TO_QUOTE

    dominant = DecisionState.READY_TO_QUOTE
    for finding in findings:
        if STATE_PRIORITY.index(finding.decision_state) > STATE_PRIORITY.index(dominant):
            dominant = finding.decision_state

    return dominant


def _has_blocking_triage(triage_results: list[TriageResult]) -> bool:
    """Returns True if any triage result is blocking."""
    return any(r.blocking for r in triage_results)


def _email_target_fields(triage_results: list[TriageResult]) -> list[str]:
    """
    Returns the minimum set of fields to request via email.
    Only producer-editable, blocking fields.
    Does not return system-owned fields — those are never emailed.
    """
    return [
        r.field_name
        for r in triage_results
        if r.triage_action == "request_via_email"
        and r.blocking
    ]


def _consolidate(
    lead_id: str,
    dominant_state: DecisionState,
    findings: list[EscalationPackage],
    triage_results: list[TriageResult],
) -> EscalationPackage:
    """
    Merges all playbook findings and triage results into one
    EscalationPackage. The dominant state drives the framing.
    """
    all_known: list[str] = []
    all_unknowable: list[str] = []
    all_mitigation: list[str] = []
    all_triage: list[TriageResult] = list(triage_results)
    uw_decision = ""

    for finding in findings:
        all_known.extend(finding.what_is_known)
        all_unknowable.extend(finding.what_is_unknowable)
        all_mitigation.extend(finding.mitigation_conditions)
        all_triage.extend(finding.triage_results)
        if finding.underwriter_decision_required:
            uw_decision = finding.underwriter_decision_required

    return EscalationPackage(
        lead_id=lead_id,
        decision_state=dominant_state,
        hard_stops=[],
        triage_results=all_triage,
        what_is_known=list(dict.fromkeys(all_known)),    # deduplicate, preserve order
        what_is_unknowable=list(dict.fromkeys(all_unknowable)),
        underwriter_decision_required=uw_decision,
        mitigation_conditions=list(dict.fromkeys(all_mitigation)),
    )