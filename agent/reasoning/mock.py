"""
Mock LLM client for local runs without credentials.
Produces deterministic reasoning output from LeadState structure.
This is a structural stand-in — not a simulation of real LLM output.
Use for pipeline testing and presentation demo stability.
"""
from __future__ import annotations
import re
from shared.ontology import LeadState, DecisionState
from agent.reasoning.llm_client import LLMClient


class MockLLMClient(LLMClient):
    """
    Generates reasoning output from LeadState fields directly.
    No API calls. No credentials required.
    Output is deterministic — same input produces same output.
    """

    def reason(self, lead_state: LeadState) -> str:
        if not lead_state.escalation:
            return self._ready_to_quote(lead_state)

        state = lead_state.decision_state

        if state == DecisionState.DECLINE:
            return self._decline(lead_state)
        if state == DecisionState.REFER:
            return self._refer(lead_state)
        if state == DecisionState.CONDITIONALLY_BINDABLE:
            return self._conditionally_bindable(lead_state)

        return self._ready_to_quote(lead_state)

    def _ready_to_quote(self, lead_state: LeadState) -> str:
        return (
            f"Lead {lead_state.lead_id} is ready to quote. "
            f"No hard stops, no blocking fields, no playbook findings. "
            f"All encoded decision paths are clear."
        )

    def _decline(self, lead_state: LeadState) -> str:
        esc = lead_state.escalation
        known = " ".join(esc.what_is_known) if esc else ""
        return (
            f"Lead {lead_state.lead_id} is recommended for decline. "
            f"{known} "
            f"No mitigation path is available for the identified conditions."
        )

    def _refer(self, lead_state: LeadState) -> str:
        esc = lead_state.escalation
        known = " ".join(esc.what_is_known) if esc else ""
        unknowable = " ".join(esc.what_is_unknowable) if esc else ""
        uw_decision = esc.underwriter_decision_required if esc else ""
        return (
            f"Lead {lead_state.lead_id} requires underwriter review. "
            f"What is known: {known} "
            f"What cannot be determined: {unknowable} "
            f"Underwriter decision required: {uw_decision}"
        )

    def _conditionally_bindable(self, lead_state: LeadState) -> str:
        esc = lead_state.escalation
        known = " ".join(esc.what_is_known) if esc else ""
        conditions = (
            " ".join(esc.mitigation_conditions)
            if esc and esc.mitigation_conditions
            else "None specified."
        )
        return (
            f"Lead {lead_state.lead_id} is conditionally bindable. "
            f"What is known: {known} "
            f"Conditions required before binding: {conditions}"
        )

    def complete(self, prompt: str) -> str:
        """
        Deterministic stand-in for a free-form LLM completion.

        Used by the qualitative eval judge (eval/qualitative/evaluator.py).
        Parses the ground-truth facts eval/qualitative/prompt.py already
        embeds in the prompt text and returns a response in the same
        CLASSIFICATION/ACTION/SCOPE/UNKNOWN_UNKNOWNS/OVERALL_SCORE
        structure a real Claude judge would use, so evaluator.py's
        parser works identically against either backend. This is a
        structural comparison, not a simulation of real judgment —
        UNKNOWN_UNKNOWNS is always NO.
        """
        expected_state = _extract(prompt, r"EXPECTED DECISION STATE:\s*(\S+)")
        actual_state = _extract(prompt, r"ACTUAL DECISION STATE:\s*(\S+)")
        classification_pass = (
            expected_state is not None and expected_state == actual_state
        )

        expected_email = _extract(
            prompt, r"EXPECTED EMAIL WARRANTED:\s*(True|False)"
        ) == "True"
        email_section = _section(prompt, "EMAIL OUTPUT:", "AGENT REASONING:")
        email_present = "No email generated." not in email_section
        action_pass = email_present == expected_email

        expected_types = _extract(
            prompt, r"EXPECTED INCOMPLETENESS TYPES:\s*(\[.*\])"
        )
        expects_unknowable = bool(expected_types) and expected_types != "[]"
        unknowable_section = _section(
            prompt, "WHAT IS UNKNOWABLE:", "UNDERWRITER DECISION REQUIRED:"
        )
        has_unknowable = unknowable_section != "None."
        scope_pass = (not expects_unknowable) or has_unknowable

        score = sum([
            0.4 if classification_pass else 0.0,
            0.3 if action_pass else 0.0,
            0.3 if scope_pass else 0.0,
        ])

        return (
            f"CLASSIFICATION: {'PASS' if classification_pass else 'FAIL'} — "
            f"expected {expected_state}, got {actual_state}.\n"
            f"ACTION: {'PASS' if action_pass else 'FAIL'} — "
            f"expected email_warranted={expected_email}, got {email_present}.\n"
            f"SCOPE: {'PASS' if scope_pass else 'FAIL'} — "
            f"{'unknowable conditions surfaced as expected' if scope_pass else 'expected unknowable conditions were not surfaced'}.\n"
            f"UNKNOWN_UNKNOWNS: NO — mock evaluator performs structural "
            f"comparison only, not genuine reasoning.\n"
            f"OVERALL_SCORE: {round(score, 2)}\n"
        )


def _extract(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _section(text: str, start_label: str, end_label: str) -> str:
    """Returns the trimmed text between two labeled prompt sections."""
    if start_label not in text:
        return ""
    after_start = text.split(start_label, 1)[1]
    section = after_start.split(end_label, 1)[0] if end_label in after_start else after_start
    return section.strip()