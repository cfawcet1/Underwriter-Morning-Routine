"""
Action routes — underwriter decisions, overrides, email sends.
These are the human-in-the-loop endpoints.
Every action is recorded — it becomes eval signal.
Thin layer — delegates to lead_service and mail_service.
"""
from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from api.models.requests import OverrideRequest, EmailSendRequest
from api.services.lead_service import record_override
from api.services.mail_service import send_email, get_emails

router = APIRouter()


@router.post("/override")
def submit_override(payload: OverrideRequest) -> dict:
    """
    Records an underwriter override decision.
    Feeds into eval/feedback/collector.py as learning signal.
    """
    result = record_override(payload.model_dump())
    return {"status": "recorded", "lead_id": payload.lead_id}


@router.post("/email/send")
def send_followup_email(payload: EmailSendRequest, request: Request) -> dict:
    """
    Sends the outbound follow-up email via the mock mailbox service.
    Records whether the underwriter edited the agent draft.
    That edit rate is an eval signal — folded into metadata so it
    reaches the mailbox record instead of being silently dropped.

    Idempotent per lead — a lead gets exactly one follow-up email, so
    a UI double-click or retry can't put two emails in front of the
    same producer.
    """
    if get_emails(payload.lead_id):
        raise HTTPException(
            status_code=409,
            detail=f"An email has already been sent for lead {payload.lead_id}.",
        )
    metadata = dict(payload.metadata or {})
    metadata["edited"] = payload.edited
    result = send_email({
        "lead_id": payload.lead_id,
        "to": payload.to,
        "subject": payload.subject,
        "body": payload.body,
        "metadata": metadata,
    })
    return {"status": "sent", "lead_id": payload.lead_id}