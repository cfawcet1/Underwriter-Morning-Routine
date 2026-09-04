"""
Anthropic Claude implementation of LLMClient.
Receives a typed LeadState — never raw lead fields.
Reasoning space is bounded by the ontology object.
"""
from __future__ import annotations
import anthropic
from shared.ontology import LeadState, DecisionState
from agent.reasoning.llm_client import LLMClient
from agent.reasoning.prompt import build_prompt


class AnthropicLLMClient(LLMClient):
    """
    Calls Claude via the Anthropic API.
    Model and max_tokens are configurable at instantiation.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def reason(self, lead_state: LeadState) -> str:
        """
        Sends a typed LeadState to Claude for reasoning.
        Returns Claude's reasoning as a string.
        The prompt is built from the ontology — never from raw fields.
        """
        prompt = build_prompt(lead_state)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        return message.content[0].text