"""
Typed contracts between the deterministic and LLM layers.
Extends shared.schema — does not replace it.
All agent output and eval input is expressed in these types.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class IncompletenessType(str, Enum):
    ABSENT_RETRIEVABLE = "missing_required"
    SYSTEM_OWNED = "missing_system_owned"
    CONTRADICTORY = "conflict"
    STRUCTURALLY_UNKNOWABLE = "unknowable"


class DecisionState(str, Enum):
    READY_TO_QUOTE = "ready_to_quote"
    DECLINE = "decline"
    REFER = "refer"
    CONDITIONALLY_BINDABLE = "conditionally_bindable"


class HardStop(BaseModel):
    field_name: str
    value: object
    reason: str


class TriageResult(BaseModel):
    field_name: str
    incompleteness_type: IncompletenessType
    triage_action: str
    blocking: bool
    minimum_sufficient: bool


class EscalationPackage(BaseModel):
    lead_id: str
    decision_state: DecisionState
    hard_stops: list[HardStop]
    triage_results: list[TriageResult]
    what_is_known: list[str]
    what_is_unknowable: list[str]
    underwriter_decision_required: str
    mitigation_conditions: list[str]


class LeadState(BaseModel):
    lead_id: str
    decision_state: DecisionState
    escalation: Optional[EscalationPackage] = None
    email_warranted: bool = False
    email_target_fields: list[str] = []


class EvalResult(BaseModel):
    lead_id: str
    track: str
    classification_accurate: Optional[bool]
    action_appropriate: bool
    output_scoped: bool
    qualitative_score: Optional[float] = None
    underwriter_confirmed: Optional[bool] = None
    notes: str