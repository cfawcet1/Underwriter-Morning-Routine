"""
Abstract LLM client interface.
Both Anthropic and Mock implementations conform to this interface.
The pipeline imports this — never the concrete implementations directly.
Swapping backends requires no changes outside this folder.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from shared.ontology import LeadState


class LLMClient(ABC):
    """
    Abstract base class for LLM reasoning over a typed LeadState.
    The client receives a LeadState — never raw lead fields.
    Its reasoning space is bounded by what the ontology contains.
    """

    @abstractmethod
    def reason(self, lead_state: LeadState) -> str:
        """
        Reasons over a typed LeadState and returns a string.
        The string is the LLM's reasoning output — used by the
        composer to frame the escalation or email.

        Args:
            lead_state: Typed output from the traverser.
                        Contains decision state, triage results,
                        escalation package, and email target fields.
                        Never contains raw lead fields.

        Returns:
            A string representing the LLM's reasoning.
            Structured as:
            - What the agent understands about this lead
            - What it cannot determine and why
            - What the underwriter is being asked to decide
            - Whether an email is warranted and what it should say
        """
        raise NotImplementedError

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """
        Sends a raw text prompt to the LLM and returns its completion.

        Used by callers that need free-form LLM output not bound to a
        LeadState — currently only the qualitative eval judge
        (eval/qualitative/evaluator.py), which scores the agent's
        reasoning against versioned criteria rather than reasoning
        over a lead itself.
        """
        raise NotImplementedError