"""
Inbound request shapes.
Mirrors the payloads the frontend sends to the API.
"""
from __future__ import annotations
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
    edited: bool