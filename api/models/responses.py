"""
Outbound response shapes.
What the API returns to the frontend.
Mirrors the pipeline result structure.
"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


class TriageSummary(BaseModel):
    auto_fetch: list[str]
    request_via_email: list[str]
    contradictory: list[str]
    unknowable: list[str]


class EscalationResponse(BaseModel):
    lead_id: str
    decision_state: str
    hard_stops: list[dict]
    what_is_known: list[str]
    what_is_unknowable: list[str]
    underwriter_decision: str
    mitigation_conditions: list[str]
    triage_summary: TriageSummary


class LeadResponse(BaseModel):
    lead_id: str
    decision_state: str
    escalation: Optional[EscalationResponse] = None
    email: Optional[dict] = None
    reasoning: Optional[str] = None


class QueueResponse(BaseModel):
    buckets: dict[str, list[LeadResponse]]
    total: int


class EvalResultResponse(BaseModel):
    lead_id: str
    track: str
    classification_accurate: Optional[bool]
    action_appropriate: bool
    output_scoped: bool
    qualitative_score: Optional[float]
    notes: str