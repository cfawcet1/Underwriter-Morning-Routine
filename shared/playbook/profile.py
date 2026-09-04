"""
Profile underwriting playbook — FigJam: Profile page.
Version: 1.0.0

Encodes the KYC decision flow and reputational risk assessment.
The agent reads from this module. It does not write to it.

Epistemic assumptions encoded here:
- KYC score is treated as a proxy for relational risk, not a direct measure.
- The score is downstream of something a human would find by looking.
- When KYC is borderline or missing, the agent surfaces the gap — it does not resolve it.
- "Profile skews more favorable / adverse" is a judgment call.
  It cannot be resolved deterministically. It routes to refer.
- OSINT instruction (Facebook, Google, lawsuit involvement) is encoded as a
  required action when KYC is missing — not as an email to the producer.
  KYC is system-owned. The agent looks. It does not ask.
"""
from __future__ import annotations
from typing import Any
from shared.ontology import (
    DecisionState,
    EscalationPackage,
    HardStop,
    TriageResult,
    IncompletenessType,
)


VERSION = "1.0.0"

KYC_ENTRY_THRESHOLD = 5
KYC_SPOTLIGHT_MAX = 7
KYC_PRIVATE_MAX = 7
KYC_HIGH_MIN = 8


def evaluate(lead_id: str, fields: dict[str, Any]) -> EscalationPackage | None:
    """
    Evaluates the Profile flow for a lead.
    Returns an EscalationPackage if the lead requires referral or decline.
    Returns None if profile is clean — proceed to next playbook page.

    KYC is system-owned. If missing, the agent assumes worst case and
    runs the diagram — it does not email the producer.
    """
    kyc = fields.get("kyc_score")

    if kyc is None:
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.REFER,
            hard_stops=[],
            triage_results=[
                TriageResult(
                    field_name="kyc_score",
                    incompleteness_type=IncompletenessType.SYSTEM_OWNED,
                    triage_action="auto_fetch",
                    blocking=True,
                    minimum_sufficient=True,
                )
            ],
            what_is_known=[
                "KYC score is system-owned and could not be retrieved.",
                "Per playbook: look up name on Facebook and Google.",
                "Explicitly check for involvement in lawsuits.",
            ],
            what_is_unknowable=[
                "Whether this insured represents reputational risk to Stand "
                "cannot be determined without OSINT review."
            ],
            underwriter_decision_required=(
                "KYC score is unavailable. OSINT review required before "
                "this lead can proceed. Does the insured's public profile "
                "represent reputational risk to Stand?"
            ),
            mitigation_conditions=[],
        )

    if kyc <= KYC_ENTRY_THRESHOLD:
        return None

    if KYC_ENTRY_THRESHOLD < kyc <= KYC_SPOTLIGHT_MAX:
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.REFER,
            hard_stops=[],
            triage_results=[],
            what_is_known=[
                f"KYC score {kyc} — in spotlight range (6-7).",
                "Required exclusions: Social Media, Libel/Slander, "
                "Defense w/in Limits.",
            ],
            what_is_unknowable=[
                "Whether required exclusions are a deal killer for this "
                "insured cannot be determined without underwriter review."
            ],
            underwriter_decision_required=(
                f"KYC score {kyc} triggers the in-spotlight branch. "
                f"Add Social Media, Libel/Slander, and Defense w/in Limits "
                f"exclusions. Are any of these exclusions a deal killer "
                f"for this insured?"
            ),
            mitigation_conditions=[],
        )

    if KYC_ENTRY_THRESHOLD < kyc <= KYC_PRIVATE_MAX:
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.REFER,
            hard_stops=[],
            triage_results=[],
            what_is_known=[
                f"KYC score {kyc} — private range (6-7).",
                "Liability excluded. Premises liability only.",
            ],
            what_is_unknowable=[
                "Whether the profile skews more favorable or adverse "
                "is a judgment call that cannot be made deterministically."
            ],
            underwriter_decision_required=(
                f"KYC score {kyc} with private profile. Premises liability "
                f"only applied. Does the overall profile skew more favorable "
                f"(accept as is) or more adverse (decline)?"
            ),
            mitigation_conditions=[],
        )

    if kyc >= KYC_HIGH_MIN:
        return EscalationPackage(
            lead_id=lead_id,
            decision_state=DecisionState.REFER,
            hard_stops=[],
            triage_results=[],
            what_is_known=[
                f"KYC score {kyc} — high risk range (8-10).",
                "Liability excluded.",
            ],
            what_is_unknowable=[
                "Whether liability exclusion is a deal killer for this "
                "insured requires underwriter judgment."
            ],
            underwriter_decision_required=(
                f"KYC score {kyc}. Liability excluded. Is this exclusion "
                f"a deal killer for this insured?"
            ),
            mitigation_conditions=[],
        )

    return None