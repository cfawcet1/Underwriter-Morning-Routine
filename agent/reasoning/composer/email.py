"""
Email composer — formats the outbound follow-up email to producer.
Produces one email. One ask. Minimum sufficient fields only.

The email is warranted only when:
- Fields are missing that are producer-editable
- Those fields are blocking
- The traverser identified them as the minimum sufficient set

An email is never generated for:
- System-owned fields (never ask a human for these)
- Contradictory fields (email does not resolve a contradiction)
- Structurally unknowable conditions (email does not resolve these)
- Non-blocking missing fields (defer to bind)

The composer formats. The reasoning layer provides the draft.
If reasoning produced an email draft, it is used.
If not, the composer generates a minimal fallback.
"""
from __future__ import annotations
from shared.ontology import LeadState
from shared.schema import Lead
from shared.registry import meta


def compose_email(
    lead: Lead,
    lead_state: LeadState,
    reasoning: str | None,
) -> dict | None:
    """
    Composes the outbound follow-up email.
    Returns a dict the API can pass to the mock mailbox service.
    Returns None if email is not warranted.

    Args:
        lead:       The inbound lead envelope.
        lead_state: Typed traverser output.
        reasoning:  LLM reasoning output — may contain an email draft.

    Returns:
        {
            lead_id:    str,
            to:         str,
            from:       str,
            subject:    str,
            body:       str,
            metadata:   dict,
        }
    """
    if not lead_state.email_warranted:
        return None

    if not lead_state.email_target_fields:
        return None

    # Extract email draft from reasoning if present
    email_draft = _extract_email_draft(reasoning)

    if email_draft:
        subject = email_draft.get("subject", _default_subject(lead))
        body = email_draft.get("body", _default_body(lead, lead_state))
    else:
        subject = _default_subject(lead)
        body = _default_body(lead, lead_state)

    return {
        "lead_id": lead.lead_id,
        "to": lead.fields.get("owner_email", "producer@example.com"),
        "from": "underwriting@stand.com",
        "subject": subject,
        "body": body,
        "metadata": {
            "target_fields": lead_state.email_target_fields,
            "generated_by": "agent/composer/email.py",
            "reasoning_used": reasoning is not None,
        },
    }


def _extract_email_draft(reasoning: str | None) -> dict | None:
    """
    Attempts to extract a structured email draft from LLM reasoning output.
    Looks for the EMAIL DRAFT section in the prompt response structure.
    Returns None if no draft is found or reasoning is None.
    """
    if not reasoning:
        return None

    if "EMAIL DRAFT" not in reasoning:
        return None

    try:
        draft_section = reasoning.split("EMAIL DRAFT")[1]
        lines = [
            l.strip()
            for l in draft_section.strip().split("\n")
            if l.strip()
        ]

        subject = None
        body_lines = []
        in_body = False

        for line in lines:
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif subject is not None:
                body_lines.append(line)
                in_body = True

        if subject and body_lines:
            return {
                "subject": subject,
                "body": "\n".join(body_lines),
            }

    except Exception:
        return None

    return None


def _default_subject(lead: Lead) -> str:
    """Fallback subject line when no LLM draft is available."""
    address = lead.fields.get("street_address", "your property")
    return f"Additional information needed — {address}"


def _default_body(lead: Lead, lead_state: LeadState) -> str:
    """
    Fallback email body when no LLM draft is available.
    Asks only for the minimum sufficient fields.
    Plain language. One ask.
    """
    first_name = lead.fields.get("first_name", "")
    last_name = lead.fields.get("last_name", "")
    address = lead.fields.get("street_address", "your property")

    field_labels = [
        meta(f).get("label", f)
        for f in lead_state.email_target_fields
    ]

    fields_list = "\n".join(f"- {label}" for label in field_labels)

    return f"""Dear {first_name} {last_name},

Thank you for your interest in coverage for {address}.

To complete our review, we need the following information:

{fields_list}

Please reply to this email with the requested details at your earliest convenience.

Best regards,
Stand Underwriting"""