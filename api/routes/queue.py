"""
Queue routes — returns the morning lead queue.
Reads from static fixtures for presentation stability.
Thin layer — delegates to lead_service.
"""
from __future__ import annotations
from fastapi import APIRouter, Request
from api.services.lead_service import get_queue

router = APIRouter()


@router.get("/")
def read_queue(request: Request) -> dict:
    """
    Returns the full morning queue — all leads triaged and bucketed.
    Buckets: ready_to_quote | decline | refer | conditionally_bindable
    """
    llm = request.app.state.llm
    return get_queue(llm)