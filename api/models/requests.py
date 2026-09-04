"""
Inbound request shapes.
Mirrors the payloads the frontend sends to the API.
"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


class OverrideRequest(BaseModel):
    lead_id: str
    decision: str
    reasoning: str
    confirmed_agent_classification: bool


class EmailSendRequest(BaseModel):
    lead_id: str
    to: str
    subject: str
    body: str
    edited: bool                              # did the underwriter edit the agent draft?
    metadata: Optional[dict[str, Any]] = None  # carries the composer's target_fields/
                                                # generated_by/reasoning_used through to
                                                # the mailbox — mirrors shared.schema.EmailIn,
                                                # the shape the mailbox service itself validates