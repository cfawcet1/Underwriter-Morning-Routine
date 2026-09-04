"""
Occupancy underwriting playbook — FigJam: Occupancy page.
Version: 1.0.0

Encodes occupancy type decision flow and conflict detection.
The agent reads from this module. It does not write to it.

Epistemic assumptions encoded here:
- Occupancy is not a blocking field for quoting — the FigJam note says
  explicitly: "you can provide the quote without this information but
  you must follow up after." This is encoded as non-blocking with a
  required post-quote follow-up flag.
- Vacant and Unoccupied are distinct categories doing different
  underwriting work. The agent does not conflate them.
- Short-term rentals with primary residence claim is a contradiction
  unless it is resolved by an existing primary policy with Stand — in
  that case it is the documented STR happy path, not a conflict.
- Duration of non-occupancy is the operative variable for the For Sale
  branch. Less than 60 days vs greater than 60 days produces
  materially different modification requirements.
- The modification list for extended non-occupancy (25% surcharge,
  100k AOP, 3% water cover, low temp alarm, twice-weekly visits) is
  encoded as mitigation conditions, not hard requirements.
  Twice-weekly visits cannot be verified by the agent — surfaces to UW.
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

# Duration threshold for non-occupancy modifications
NON_OCCUPANCY_THRESHOLD_DAYS = 60
MONTHS_TO_DAYS = 30


def evaluate(lead_id: str, fields: dict[str, Any]) -> EscalationPackage | None:
    """
    Evaluates the Occupancy flow for a lead.
    Returns an EscalationPackage if the lead requires referral,
    modification, or decline.
    Returns None if occupancy is clean.

    Note: occupancy missing is non-blocking per FigJam.
    A post-quote follow-up is flagged but quoting proceeds.
    """
    dwelling_use = fields.get("dwelling_use_type")
    is_rental = fields.get("is_rental")
    months_unoccupied = fields.get("months_unoccupied", 0)
    has_primary = fields.get("has_primary_policy_with_stand", False)
    listed_for_sale = fields.get("listed_for_sale", False)
    coverage_a = fields.get("coverage_a", 0)

    # Occupancy missing — non-blocking per FigJam note
    # Quote proceeds, follow-up required after
    if dwelling_use is None:
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.READY_TO_QUOTE,
            hard_stops=[],
            triage_results=[
                TriageResult(
                    field_name="dwelling_use_type",
                    incompleteness_type=IncompletenessType.ABSENT_RETRIEVABLE,
                    triage_action="request_via_email",
                    blocking=False,
                    minimum_sufficient=True,
                )
            ],
            what_is_known=[
                "Occupancy type is missing.",
                "Per playbook: quote can proceed without this information.",
                "Follow-up required after quote is issued.",
            ],
            what_is_unknowable=[],
            underwriter_decision_required="",
            mitigation_conditions=[
                "Follow up with producer for occupancy type after quote."
            ],
        )

    # Contradiction detection — owner-occupied claim conflicts with signals
    if _is_contradictory(dwelling_use, is_rental, months_unoccupied, has_primary):
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.REFER,
            hard_stops=[],
            triage_results=[
                TriageResult(
                    field_name="dwelling_use_type",
                    incompleteness_type=IncompletenessType.CONTRADICTORY,
                    triage_action="refer",
                    blocking=True,
                    minimum_sufficient=True,
                )
            ],
            what_is_known=[
                f"Dwelling use type: {dwelling_use}.",
                f"Rental status: {is_rental}.",
                f"Months unoccupied: {months_unoccupied}.",
            ],
            what_is_unknowable=[
                "The true occupancy status cannot be determined from "
                "contradictory signals without underwriter review."
            ],
            underwriter_decision_required=(
                "Occupancy signals are contradictory. "
                f"Insured claims {dwelling_use} but signals suggest "
                f"rental or vacancy. What is the true occupancy status?"
            ),
            mitigation_conditions=[],
        )

    # Short-term rentals
    if is_rental == "Short-Term Rentals":
        if has_primary and coverage_a >= 5_000_000:
            return EscalationPackage(
                lead_id=lead_id,
                decision_state=DecisionState.CONDITIONALLY_BINDABLE,
                hard_stops=[],
                triage_results=[],
                what_is_known=[
                    "Short-term rental with primary policy with Stand.",
                    f"Coverage A: ${coverage_a:,} — qualifies as lead line.",
                ],
                what_is_unknowable=[],
                underwriter_decision_required="",
                mitigation_conditions=[
                    "Write with 15% surcharge.",
                    "Attach STR endorsement.",
                ],
            )
        elif has_primary:
            return EscalationPackage(
                lead_id=lead_id,
                decision_state=DecisionState.CONDITIONALLY_BINDABLE,
                hard_stops=[],
                triage_results=[],
                what_is_known=["Short-term rental with primary policy with Stand."],
                what_is_unknowable=[],
                underwriter_decision_required="",
                mitigation_conditions=[
                    "Write with 15% surcharge.",
                    "Attach STR endorsement.",
                ],
            )
        else:
            return EscalationPackage(
                lead_id=lead_id,
                decision_state=DecisionState.DECLINE,
                hard_stops=[],
                triage_results=[],
                what_is_known=[
                    "Short-term rental with no primary policy with Stand.",
                    "No justifiable exception.",
                ],
                what_is_unknowable=[],
                underwriter_decision_required="",
                mitigation_conditions=[],
            )

    # Long-term rentals
    if is_rental == "Long-Term Rentals":
        if has_primary:
            return EscalationPackage(
                lead_id=lead_id,
                decision_state=DecisionState.CONDITIONALLY_BINDABLE,
                hard_stops=[],
                triage_results=[],
                what_is_known=["Long-term rental with primary policy with Stand."],
                what_is_unknowable=[],
                underwriter_decision_required="",
                mitigation_conditions=["Write with 15% surcharge."],
            )
        else:
            return EscalationPackage(
                lead_id=lead_id,
                decision_state=DecisionState.REFER,
                hard_stops=[],
                triage_results=[],
                what_is_known=["Long-term rental without primary policy with Stand."],
                what_is_unknowable=[
                    "Whether this qualifies as a lead line for a "
                    "larger desirable account requires underwriter judgment."
                ],
                underwriter_decision_required=(
                    "Long-term rental without primary Stand policy. "
                    "Is this a lead line for a larger desirable account?"
                ),
                mitigation_conditions=[],
            )

    # For sale
    if listed_for_sale:
        days_unoccupied = months_unoccupied * MONTHS_TO_DAYS
        if days_unoccupied < NON_OCCUPANCY_THRESHOLD_DAYS:
            return EscalationPackage(
                lead_id=lead_id,
                decision_state=DecisionState.CONDITIONALLY_BINDABLE,
                hard_stops=[],
                triage_results=[],
                what_is_known=[
                    f"Property listed for sale.",
                    f"Unoccupied for {months_unoccupied} months "
                    f"({days_unoccupied} days) — under 60 day threshold.",
                ],
                what_is_unknowable=[],
                underwriter_decision_required="",
                mitigation_conditions=[
                    "Apply 25% surcharge.",
                    "Cap AOP at $100k.",
                    "Apply 3% water cover.",
                    "Require low temperature alarm or winterization in cold climates.",
                    "Require twice-weekly interior and exterior visits — "
                    "agent cannot verify, underwriter must confirm.",
                ],
            )
        else:
            return EscalationPackage(
                lead_id=lead_id,
                decision_state=DecisionState.DECLINE,
                hard_stops=[],
                triage_results=[],
                what_is_known=[
                    f"Property listed for sale.",
                    f"Unoccupied for {months_unoccupied} months "
                    f"({days_unoccupied} days) — exceeds 60 day threshold.",
                    "No justifiable exception.",
                ],
                what_is_unknowable=[],
                underwriter_decision_required="",
                mitigation_conditions=[],
            )

    # Primary residence, no rental, not for sale — clean
    return None


def _is_contradictory(
    dwelling_use: str,
    is_rental: str | None,
    months_unoccupied: int,
    has_primary: bool,
) -> bool:
    """
    Detects the three occupancy conflict variants from archetypes.py:
    - Owner-occupied but unoccupied for months
    - Primary residence but running short-term rentals, with no
      existing primary policy with Stand to resolve it (if there is
      one, this is the documented STR happy path below, not a conflict)
    - Owner-occupied but secondary use type
    """
    if dwelling_use == "Primary" and is_rental == "Short-Term Rentals" and not has_primary:
        return True
    if dwelling_use == "Primary" and months_unoccupied >= 3:
        return True
    return False