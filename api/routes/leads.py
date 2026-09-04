"""
Lead routes — individual lead detail and pipeline result.
Thin layer — delegates to lead_service.
"""
from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from api.services.lead_service import get_lead, run_lead

router = APIRouter()


@router.get("/{lead_id}")
def read_lead(lead_id: str, request: Request) -> dict:
    """
    Returns the full pipeline result for a single lead.
    Includes decision state, escalation, email, and reasoning.
    """
    llm = request.app.state.llm
    result = get_lead(lead_id, llm)
    if not result:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found.")
    return result


@router.post("/{lead_id}/run")
def rerun_lead(lead_id: str, request: Request) -> dict:
    """
    Re-runs the pipeline against a lead.
    Useful when a field has been updated or a response received.
    """
    llm = request.app.state.llm
    result = run_lead(lead_id, llm)
    if not result:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found.")
    return result