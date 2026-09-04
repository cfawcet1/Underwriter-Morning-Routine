"""
Builds the LLM prompt from a typed LeadState.
The LLM never receives raw lead fields.
Its reasoning space is bounded by what the ontology contains.

The prompt is versioned. When the epistemological framework changes,
this file changes. The version string makes that change reviewable.
"""
from __future__ import annotations
from shared.ontology import LeadState, DecisionState


PROMPT_VERSION = "1.0.0"


def build_prompt(lead_state: LeadState) -> str:
    """
    Constructs a structured prompt from a typed LeadState.
    Includes decision state, triage findings, escalation context,
    and a precise framing of what the LLM is being asked to do.
    """
    esc = lead_state.escalation
    state = lead_state.decision_state

    known = (
        "\n".join(f"- {k}" for k in esc.what_is_known)
        if esc and esc.what_is_known
        else "None."
    )

    unknowable = (
        "\n".join(f"- {u}" for u in esc.what_is_unknowable)
        if esc and esc.what_is_unknowable
        else "None."
    )

    mitigation = (
        "\n".join(f"- {m}" for m in esc.mitigation_conditions)
        if esc and esc.mitigation_conditions
        else "None."
    )

    uw_decision = (
        esc.underwriter_decision_required
        if esc and esc.underwriter_decision_required
        else "No underwriter decision required."
    )

    email_fields = (
        "\n".join(f"- {f}" for f in lead_state.email_target_fields)
        if lead_state.email_target_fields
        else "None."
    )

    return f"""You are an underwriting assistant reasoning over a
pre-classified lead. You do not have access to raw lead data.
You reason only over what the deterministic pipeline has already
established. Your job is to surface the unknown unknowns —
the signals that no single field captures — and frame the
situation precisely for the underwriter.

PROMPT VERSION: {PROMPT_VERSION}
LEAD ID: {lead_state.lead_id}
DECISION STATE: {state.value}

WHAT IS KNOWN:
{known}

WHAT CANNOT BE DETERMINED DETERMINISTICALLY:
{unknowable}

UNDERWRITER DECISION REQUIRED:
{uw_decision}

MITIGATION CONDITIONS (if conditionally bindable):
{mitigation}

FIELDS TO REQUEST VIA EMAIL (minimum sufficient set):
{email_fields}

YOUR TASK:

1. Review the known facts and the unknowable conditions above.

2. Identify any signals in the combination of known facts that
   suggest additional risk the deterministic pipeline may not
   have captured. These are the unknown unknowns — the gestalt
   flags an experienced underwriter would notice.

3. Frame the situation for the underwriter in plain language.
   Be precise about what you know, what you don't know, and
   what you are asking them to decide. Do not speculate beyond
   what the known facts support.

4. If an email is warranted, draft one clear, minimal message
   that asks for exactly the fields listed above — nothing more.
   One email. One ask. The underwriter sends it or edits it.

5. If this lead is conditionally bindable, confirm the mitigation
   conditions are clearly stated and actionable.

Respond in the following structure:

REASONING:
[Your assessment of the risk gestalt — what the combination of
known facts suggests that no single field captures]

UNDERWRITER FRAMING:
[Plain language summary of what the underwriter needs to know
and decide, precise enough to act on in ten seconds]

EMAIL DRAFT (if warranted):
[One clear email to the producer or applicant. Subject line
and body. Ask only for the minimum sufficient fields.]
"""