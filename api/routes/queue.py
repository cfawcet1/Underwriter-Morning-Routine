"""
Queue routes — returns the morning lead queue.
Reads from static fixtures for presentation stability.
Thin layer — delegates to lead_service.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Request, Query
from api.services.lead_service import get_queue, generate_live_queue

router = APIRouter()


@router.get("/")
def read_queue(request: Request) -> dict:
    """
    Returns the full morning queue — all leads triaged and bucketed.
    Buckets: ready_to_quote | decline | refer | conditionally_bindable
    """
    llm = request.app.state.llm
    return get_queue(llm)


@router.post("/generate")
def generate_queue(
    request: Request,
    count: int = Query(default=10, ge=1, le=100),
    seed: Optional[int] = Query(default=None),
    difficulty: str = Query(default="mixed"),
) -> dict:
    """
    Pulls a fresh queue from the leadgen service and triages it.
    Additive to GET / — the fixture-based queue stays the eval
    harness's ground truth; this is for live development/demo runs.
    """
    llm = request.app.state.llm
    return generate_live_queue(llm, count=count, seed=seed, difficulty=difficulty)