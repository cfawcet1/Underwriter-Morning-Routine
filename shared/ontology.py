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
    ABSENT_RETRIEVABLE = "missing_required"        # producer-editable, email resolves it
    SYSTEM_OWNED = "missing_system_owned"          # agent must fetch/derive, never email
    CONTRADICTORY = "conflict"                     # internal contradiction, refer to UW
    STRUCTURALLY_UNKNOWABLE = "unknowable"         # no retrieval resolves this, UW judgment


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
    triage_action: str                             # auto_fetch | request_via_email | defer_to_bind | refer | unknowable
    blocking: bool                                 # does this prevent quoting
    minimum_sufficient: bool                       # resolving this unblocks the most downstream decisions


class EscalationPackage(BaseModel):
    lead_id: str
    decision_state: DecisionState
    hard_stops: list[HardStop]
    triage_results: list[TriageResult]
    what_is_known: list[str]
    what_is_unknowable: list[str]
    underwriter_decision_required: str            # one sentence — what is the UW being asked to decide
    mitigation_conditions: list[str]              # empty unless conditionally_bindable


class LeadState(BaseModel):