"""
Mock LLM client for local runs without credentials.
Produces deterministic reasoning output from LeadState structure.
This is a structural stand-in — not a simulation of real LLM output.
Use for pipeline testing and presentation demo stability.
"""
from __future__ import annotations
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