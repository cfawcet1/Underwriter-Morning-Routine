"""
Mail service — bridge between routes and mock mailbox.
Calls the provided mock mailbox service via HTTP.
Routes never call the mailbox directly — they go through here.
"""
from __future__ import annotations
import os
import httpx

MAILBOX_URL = os.environ.get("MAILBOX_URL", "http://localhost:8001")


def send_email(payload: dict) -> dict:
    """
    Sends an outbound email via the mock mailbox service.
    Payload shape matches shared.schema.EmailIn.
    """
    with httpx.Client() as client:
        response = client.post(
            f"{MAILBOX_URL}/emails",
            json={
                "lead_id": payload["lead_id"],
                "to": payload["to"],
                "from": payload.get("from", "underwriting@stand.com"),
                "subject": payload["subject"],
                "body": payload["body"],
                "metadata": payload.get("metadata", {}),
            },
        )
        response.raise_for_status()
        return response.json()


def get_emails(lead_id: str) -> list[dict]:
    """
    Retrieves all emails sent for a lead from the mock mailbox.
    """
    with httpx.Client() as client:
        response = client.get(
            f"{MAILBOX_URL}/emails",
            params={"lead_id": lead_id},
        )
        response.raise_for_status()
        return response.json()