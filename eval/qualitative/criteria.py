"""
Qualitative eval criteria — the epistemic framework as versioned
evaluation criteria. This is what the qualitative evaluator scores
agent reasoning against. Not vibes. Not a rubric. A document.

When the epistemological framework changes, this file changes.
The version string makes that change reviewable and diffable.

Three dimensions, each scored independently:
    classification_accurate — did the agent correctly identify what
                              kind of incompleteness it was dealing with?
    action_appropriate      — did the agent take the right action for
                              that classification?
    output_scoped           — did the agent produce output that was
                              precisely scoped to what was needed?
"""
from __future__ import annotations

VERSION = "1.0.0"

INCOMPLETENESS_CLASSIFICATIONS = """
There are four types of incompleteness. The agent must correctly
identify which type it is dealing with before taking any action.

1. ABSENT_RETRIEVABLE
   The field is missing and the producer or applicant can supply it.
   The field is marked editableByProducer: true in the field registry.
   The correct action is to request it via email — one email, one ask,
   minimum sufficient fields only.

2. SYSTEM_OWNED
   The field is missing and must be auto-fetched or derived by the system.
   The field is marked editableByProducer: false in the field registry.
   The correct action is to fetch or derive it. Never email a human for
   a system-owned field.

3. CONTRADICTORY
   A field is present but conflicts with another field.
   No email resolves a contradiction.
   The correct action is to refer to the underwriter with a precise
   description of the contradiction and its implications.

4. STRUCTURALLY_UNKNOWABLE
   No retrieval, derivation, or email will resolve this condition.
   It requires underwriter judgment — human experience applied to
   a combination of signals that no single field captures.
   The correct action is to refer to the underwriter with a precise
   description of what is unknowable and what decision is being asked for.
"""

ACTION_CRITERIA = """
The correct action depends entirely on the correct classification.

ABSENT_RETRIEVABLE → request_via_email
    - One email only
    - Ask for minimum sufficient fields — not everything that is missing
    - Never ask for system-owned fields in the email
    - The email must be targeted enough that a producer can answer it
      without calling the underwriter for clarification

SYSTEM_OWNED → auto_fetch
    - Never surfaces to a human
    - Agent fetches or derives the value
    - If derivation fails, escalate with a precise description of why

CONTRADICTORY → refer
    - Escalation package must name the specific fields in conflict
    - Must explain what the contradiction implies for the risk
    - Must state precisely what the underwriter is being asked to resolve

STRUCTURALLY_UNKNOWABLE → refer
    - Escalation package must name what is unknowable and why
    - Must state what the agent determined from what was present
    - Must frame the underwriter decision in one sentence
    - Precise enough to act on in ten seconds
"""

SCOPE_CRITERIA = """
Output scope is the measure of precision. An agent that asks for
everything that is technically missing has failed the scope test
even if it asked for the right things.

For email output:
    - The email asks only for blocking fields
    - The email asks only for producer-editable fields
    - The email asks for the minimum sufficient set —
      the fields whose resolution unblocks the most downstream decisions
    - One email. One ask. Not a checklist.

For escalation output:
    - what_is_known contains only facts the deterministic pipeline
      established — not inferences or assumptions
    - what_is_unknowable contains only conditions that genuinely
      cannot be resolved — not fields that are merely missing
    - underwriter_decision_required is one sentence
    - mitigation_conditions are actionable and specific
    - The underwriter can act on the escalation in ten seconds
      without asking a follow-up question
"""

UNKNOWN_UNKNOWNS_CRITERIA = """
The highest value signal an agent can surface is the unknown unknown —
the condition that no single field captures, the combination of signals
that suggests an exposure the playbook didn't anticipate.

A high-scoring agent notices:
    - Combinations of conditions that together suggest a risk category
      not explicitly encoded in the playbook
    - Proxy variables that may be unreliable for this specific lead
    - Patterns in the known facts that an experienced underwriter would
      flag even when no individual field triggers a rule
    - The gestalt of the lead — what does the combination of everything
      known suggest about the nature of this risk?

A low-scoring agent:
    - Only reports what the playbook explicitly told it
    - Treats each field in isolation
    - Misses the signal that lives in the relationship between fields
    - Produces output that could have been generated by a decision tree
"""