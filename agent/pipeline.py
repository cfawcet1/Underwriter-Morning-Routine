"""
Pipeline — orchestrates the three agent layers in sequence.
Scanner → Traverser → Reasoning (when warranted) → Composer.

This is the only file that knows the sequence.
Each layer receives the output of the previous layer.
No layer imports from another layer directly.
All inter-layer communication is through shared.ontology types.

Sequence:
    1. Scanner  — hard stops, deterministic, no LLM
                  if hard stops found → composer (decline), done
    2. Traverser — playbook traversal, field triage, incompleteness
                   classification, dominant state resolution
                   if ready to quote and no email needed → done
    3. Reasoning — LLM inference over typed LeadState
                   only runs when traverser finds genuine ambiguity
                   or unknowable conditions
    4. Composer  — formats output for underwriter
                   email, escalation, or clean quote signal
"""
from __future__ import annotations
from typing import Any
from shared.ontology import DecisionState, LeadState
from shared.schema import Lead
import agent.scanner as scanner
import agent.traverser as traverser
from agent.composer.escalation import compose_escalation
from agent.composer.email import compose_email
from agent.reasoning.llm_client import LLMClient


def run(lead: Lead, llm: LLMClient) -> dict[str, Any]:
    """
    Runs the full agent pipeline against a single lead.
    Returns a structured result dict the API layer can serialize.

    Args:
        lead:   The inbound lead from the queue.
        llm:    The LLM client instance (Anthropic or Mock).

    Returns:
        {
            lead_id:        str,
            decision_state: str,
            escalation:     dict | None,
            email:          dict | None,
            reasoning:      str | None,
        }
    """
    fields = lead.fields

    # --- Stage 1: Scanner ---
    # Hard stops only. No LLM. No playbook traversal.
    # If hard stops found, pipeline ends here.
    scan_result = scanner.run(lead.lead_id, fields)

    if scan_result.decision_state == DecisionState.DECLINE \
            and scan_result.escalation \
            and scan_result.escalation.hard_stops:
        return _format_result(
            lead_state=scan_result,
            email=None,
            reasoning=None,
        )

    # --- Stage 2: Traverser ---
    # Playbook traversal, field triage, dominant state resolution.
    # Deterministic. No LLM.
    traverse_result = traverser.run(lead.lead_id, fields)

    # Clean lead — ready to quote, no email needed
    if traverse_result.decision_state == DecisionState.READY_TO_QUOTE \
            and not traverse_result.email_warranted:
        return _format_result(
            lead_state=traverse_result,
            email=None,
            reasoning=None,
        )

    # --- Stage 3: Reasoning ---
    # LLM inference over typed LeadState.
    # Only runs when the traverser found genuine ambiguity,
    # unknowable conditions, or a refer state.
    # Never receives raw lead fields — only the typed LeadState.
    reasoning_text = None

    if traverse_result.decision_state in (
        DecisionState.REFER,
        DecisionState.CONDITIONALLY_BINDABLE,
    ) or traverse_result.email_warranted:
        reasoning_text = llm.reason(traverse_result)

    # --- Stage 4: Composer ---
    # Formats the output for the underwriter.
    # Email composer runs only when email is warranted.
    # Escalation composer runs for refer and conditionally bindable.
    email_output = None
    if traverse_result.email_warranted:
        email_output = compose_email(
            lead=lead,
            lead_state=traverse_result,
            reasoning=reasoning_text,
        )

    return _format_result(
        lead_state=traverse_result,
        email=email_output,
        reasoning=reasoning_text,
    )


def _format_result(
    lead_state: LeadState,
    email: dict | None,
    reasoning: str | None,
) -> dict[str, Any]:
    """
    Serializes the pipeline output into a dict the API can return.
    Escalation is formatted by the escalation composer if present.
    """
    escalation_output = None
    if lead_state.escalation:
        escalation_output = compose_escalation(lead_state.escalation)

    return {
        "lead_id": lead_state.lead_id,
        "decision_state": lead_state.decision_state.value,
        "escalation": escalation_output,
        "email": email,
        "reasoning": reasoning,
    }