"""
Action routes — underwriter decisions, overrides, email sends.
These are the human-in-the-loop endpoints.
Every action is recorded — it becomes eval signal.
Thin layer — delegates to lead_service and mail_service.
"""
from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from api.services.lead_service import record_override
from api.services.mail_service import send_email, get_emails

router = APIRouter()


class OverridePayload(BaseModel):
    lead_id: str
    decision: str                  # the underwriter's decision
    reasoning: str                 # why they made it
    confirmed_agent_classification: bool  # did the agent classify correctly?


class EmailPayload(BaseModel):
    lead_id: str
    to: str
    subject: str
    body: str
    edited: bool                   # did the underwriter edit the agent draft?


@router.post("/override")
def submit_override(payload: OverridePayload) -> dict:
    """
    Records an underwriter override decision.
    Feeds into eval/feedback/collector.py as learning signal.
    """
    result = record_override(payload.model_dump())
    return {"status": "recorded", "lead_id": payload.lead_id}


@router.post("/email/send")
def send_followup_email(payload: EmailPayload, request: Request) -> dict:
    """
    Sends the outbound follow-up email via the mock mailbox service.
    Records whether the underwriter edited the agent draft.
    That edit rate is an eval signal.

    Idempotent per lead — a lead gets exactly one follow-up email, so
    a UI double-click or retry can't put two emails in front of the
    same producer.
    """
    if get_emails(payload.lead_id):
        raise HTTPException(
            status_code=409,
            detail=f"An email has already been sent for lead {payload.lead_id}.",
        )
    result = send_email(payload.model_dump())
    return {"status": "sent", "lead_id": payload.lead_id}