"""
PC 9 & 10 underwriting playbook — FigJam: PC 9 & 10 page.
Version: 1.0.0

Encodes the fire protection classification decision flow for
properties at or assumed to be at Protection Class 9 or 10.

The agent reads from this module. It does not write to it.

Epistemic assumptions encoded here:
- Protection class defaults to 9 when missing (field registry
  missingDefault). This is encoded as the entry condition.
  The agent assumes worst case and runs the full diagram.
- Water source availability is more fundamental than response time.
  This ordering reflects hard-won knowledge from the Palisades fire.
  Infrastructure that checks out on paper can fail under simultaneous
  peak demand. Response capability without suppression capability
  is insufficient. The diagram is traversed in this order deliberately.
- Square footage thresholds (7500 and 4000 sq ft) are proxies for
  water demand, not arbitrary size categories. Larger homes require
  more gallons per square foot to suppress a fire. The agent knows
  this is what square footage means in this context.
- Volunteer vs paid responders produce different requirements because
  volunteer departments have activation lag that paid departments
  do not. This is actuarial loss experience encoded as a rule.
- The yellow mitigation nodes represent a negotiation state —
  conditionally bindable pending mitigation. This is Stand's
  collaborative philosophy encoded structurally.
- Twice-weekly visits and some mitigation conditions cannot be
  verified by the agent. These surface to the underwriter explicitly.
- Road access is system-owned — the agent derives it, never asks.
- Alternative water source, fire dept response time, interior
  sprinklers, and physical barriers are conditionally required
  at PC 9/10 and are producer-editable — email warranted when missing.
"""
from __future__ import annotations
from typing import Any
from shared.ontology import (
    DecisionState,
    EscalationPackage,
    TriageResult,
    IncompletenessType,
)


VERSION = "1.0.0"

# Square footage thresholds — proxies for water demand
SQ_FT_LARGE = 7500
SQ_FT_MEDIUM = 4000

# Hydrant proximity threshold
HYDRANT_THRESHOLD_FT = 1000

# Response time bands
RESPONSE_WITHIN_15 = "Within 15 Minutes"
RESPONSE_15_TO_30 = "Between 15 and 30 Minutes"
RESPONSE_OVER_30 = "Greater than 30 Minutes"


def evaluate(lead_id: str, fields: dict[str, Any]) -> EscalationPackage | None:
    """
    Evaluates the PC 9 & 10 flow for a lead.

    Entry condition: protection_class is 9 or 10, or null (defaults to 9).
    Returns None if protection class is not 9 or 10 — not this page's concern.
    Returns EscalationPackage for all other outcomes.
    """
    pc = fields.get("protection_class")

    # Apply missingDefault from field registry
    if pc is None:
        pc = 9

    # Not a PC 9/10 lead — this page does not apply
    if str(pc) not in ("9", "10"):
        return None

    sq_ft = fields.get("square_feet", 0)
    hydrant_dist = fields.get("dist_to_nearest_fire_hydrant")
    road_access = fields.get("road_access")
    response_time = fields.get("fire_dept_response_time")
    fd_type = fields.get("fire_department_type")
    alt_water = fields.get("alternative_water_source")
    sprinklers = fields.get("interior_sprinklers")
    physical_barriers = fields.get("physical_barriers")

    # --- Road access check (system-owned, agent derives) ---
    if road_access == "Limited / Dead-end / No Turnaround":
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.DECLINE,
            hard_stops=[],
            triage_results=[
                TriageResult(
                    field_name="road_access",
                    incompleteness_type=IncompletenessType.SYSTEM_OWNED,
                    triage_action="auto_fetch",
                    blocking=True,
                    minimum_sufficient=True,
                )
            ],
            what_is_known=[
                f"Protection class: {pc}.",
                "Road access: limited, dead-end, or no turnaround.",
                "Fire apparatus cannot safely access the property.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required="",
            mitigation_conditions=[],
        )

    # --- Water source assessment (more fundamental than response time) ---

    # Hydrant within 1000 feet
    hydrant_present = (
        hydrant_dist is not None and hydrant_dist <= HYDRANT_THRESHOLD_FT
    )

    if hydrant_present:
        return _evaluate_with_hydrant(
            lead_id, fields, pc, sq_ft, response_time,
            fd_type, physical_barriers, sprinklers
        )

    # No hydrant — check alternative water source
    if alt_water is None:
        # Conditionally required at PC 9/10, producer-editable
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.REFER,
            hard_stops=[],
            triage_results=[
                TriageResult(
                    field_name="alternative_water_source",
                    incompleteness_type=IncompletenessType.ABSENT_RETRIEVABLE,
                    triage_action="request_via_email",
                    blocking=True,
                    minimum_sufficient=True,
                )
            ],
            what_is_known=[
                f"Protection class: {pc}.",
                f"No hydrant within {HYDRANT_THRESHOLD_FT} feet.",
                "Alternative water source status unknown.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required=(
                "No hydrant within 1000 feet and alternative water source "
                "is unknown. Request alternative water source information "
                "from producer before proceeding."
            ),
            mitigation_conditions=[],
        )

    if not alt_water:
        # No hydrant, no alternative water — decline
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.DECLINE,
            hard_stops=[],
            triage_results=[],
            what_is_known=[
                f"Protection class: {pc}.",
                f"No hydrant within {HYDRANT_THRESHOLD_FT} feet.",
                "No alternative water source available.",
                "Suppression capability insufficient.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required="",
            mitigation_conditions=[],
        )

    # Alternative water source present — check if year-round accessible
    alt_water_year_round = fields.get("alternative_water_source")

    # --- Response time assessment ---
    if response_time is None:
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.REFER,
            hard_stops=[],
            triage_results=[
                TriageResult(
                    field_name="fire_dept_response_time",
                    incompleteness_type=IncompletenessType.ABSENT_RETRIEVABLE,
                    triage_action="request_via_email",
                    blocking=True,
                    minimum_sufficient=True,
                )
            ],
            what_is_known=[
                f"Protection class: {pc}.",
                "Alternative water source present.",
                "Fire department response time unknown.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required=(
                "Alternative water source present but response time unknown. "
                "Request fire department response time from producer."
            ),
            mitigation_conditions=[],
        )

    if response_time == RESPONSE_OVER_30:
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.DECLINE,
            hard_stops=[],
            triage_results=[],
            what_is_known=[
                f"Protection class: {pc}.",
                "Alternative water source present.",
                "Fire department response time: greater than 30 minutes.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required="",
            mitigation_conditions=[],
        )

    # Response within 15 or 15-30 minutes — evaluate staffing and size
    return _evaluate_with_water_and_response(
        lead_id, fields, pc, sq_ft, response_time, fd_type, sprinklers
    )


def _evaluate_with_hydrant(
    lead_id: str,
    fields: dict[str, Any],
    pc: int,
    sq_ft: int,
    response_time: str | None,
    fd_type: str | None,
    physical_barriers: bool | None,
    sprinklers: str | None,
) -> EscalationPackage:
    """
    Hydrant present within 1000 feet.
    Response time is the next gate.
    """
    if response_time is None:
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.REFER,
            hard_stops=[],
            triage_results=[
                TriageResult(
                    field_name="fire_dept_response_time",
                    incompleteness_type=IncompletenessType.ABSENT_RETRIEVABLE,
                    triage_action="request_via_email",
                    blocking=True,
                    minimum_sufficient=True,
                )
            ],
            what_is_known=[
                f"Protection class: {pc}.",
                "Hydrant within 1000 feet — water supply confirmed.",
                "Fire department response time unknown.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required=(
                "Hydrant confirmed within 1000 feet. "
                "Request fire department response time from producer."
            ),
            mitigation_conditions=[],
        )

    if response_time == RESPONSE_OVER_30:
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.DECLINE,
            hard_stops=[],
            triage_results=[],
            what_is_known=[
                f"Protection class: {pc}.",
                "Hydrant within 1000 feet.",
                "Fire department response time: greater than 30 minutes.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required="",
            mitigation_conditions=[],
        )

    if response_time == RESPONSE_WITHIN_15 and sq_ft < SQ_FT_LARGE:
        # Clean write — the only clean write on this page
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.READY_TO_QUOTE,
            hard_stops=[],
            triage_results=[],
            what_is_known=[
                f"Protection class: {pc}.",
                "Hydrant within 1000 feet.",
                f"Response time within 15 minutes.",
                f"Square footage {sq_ft} — under 7500 sq ft threshold.",
                "Okay to write.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required="",
            mitigation_conditions=[],
        )

    # Response 15-30 minutes or large home — evaluate staffing
    return _evaluate_staffing_and_size(
        lead_id, fields, pc, sq_ft, response_time, fd_type, sprinklers
    )


def _evaluate_with_water_and_response(
    lead_id: str,
    fields: dict[str, Any],
    pc: int,
    sq_ft: int,
    response_time: str,
    fd_type: str | None,
    sprinklers: str | None,
) -> EscalationPackage:
    """
    Alternative water source present, response time known and acceptable.
    Evaluate staffing and size requirements.
    """
    return _evaluate_staffing_and_size(
        lead_id, fields, pc, sq_ft, response_time, fd_type, sprinklers
    )


def _evaluate_staffing_and_size(
    lead_id: str,
    fields: dict[str, Any],
    pc: int,
    sq_ft: int,
    response_time: str,
    fd_type: str | None,
    sprinklers: str | None,
) -> EscalationPackage:
    """
    Volunteer vs paid responders produce different water requirements.
    This encodes actuarial loss experience — volunteer departments have
    activation lag that paid departments do not.
    Square footage thresholds are proxies for water demand, not size categories.
    """
    is_volunteer = fd_type in ("Volunteer", "Mostly Volunteer", "Unknown")
    physical_barriers = fields.get("physical_barriers", False)

    # Determine water requirement based on staffing and size
    if sq_ft > SQ_FT_LARGE:
        # Largest homes — decline regardless of staffing
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.DECLINE,
            hard_stops=[],
            triage_results=[],
            what_is_known=[
                f"Protection class: {pc}.",
                f"Square footage {sq_ft} exceeds 7500 sq ft threshold.",
                f"Response time: {response_time}.",
                f"Staffing: {'volunteer' if is_volunteer else 'paid'}.",
                "Water demand exceeds suppression capability.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required="",
            mitigation_conditions=[],
        )

    # Determine gallons per square foot requirement
    if sq_ft > SQ_FT_MEDIUM:
        # 4000-7500 sq ft range
        gpf = 20 if not is_volunteer else 20
        sprinkler_required = True
    else:
        # Under 4000 sq ft
        gpf = 10
        sprinkler_required = sq_ft > SQ_FT_MEDIUM

    mitigation = [
        f"Require {gpf} gallons water per square foot.",
    ]

    if sprinkler_required:
        mitigation.append(
            "Require centrally monitored interior sprinklers."
        )

    if physical_barriers:
        mitigation.extend([
            "Require Knox Box within underwriting period.",
            "Central station fire alarm required.",
        ])

    # Check sprinkler compliance if required
    if sprinkler_required:
        if sprinklers != "Centrally Monitored Interior Sprinklers":
            mitigation.append(
                "Centrally monitored interior sprinklers not confirmed — "
                "required before binding."
            )

    return EscalationPackage(
        lead_id=lead_id,
        decision_state=DecisionState.CONDITIONALLY_BINDABLE,
        hard_stops=[],
        triage_results=[],
        what_is_known=[
            f"Protection class: {pc}.",
            f"Square footage: {sq_ft}.",
            f"Response time: {response_time}.",
            f"Staffing: {'volunteer' if is_volunteer else 'paid'}.",
        ],
        what_is_unknowable=[],
        underwriter_decision_required=(
            "Property is conditionally bindable. "
            "Confirm all mitigation conditions are satisfied "
            "before binding."
        ) if mitigation else "",
        mitigation_conditions=mitigation,
    )