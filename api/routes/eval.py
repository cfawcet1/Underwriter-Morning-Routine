"""
Eval routes — surfaces eval results and patterns to the frontend.
Read-only. Eval loop writes results — this layer only reads them.
Thin layer — delegates to eval_service.
"""
from __future__ import annotations
from fastapi import APIRouter
from api.services.eval_service import get_eval_results, get_patterns

router = APIRouter()


@router.get("/results")
def read_eval_results() -> dict:
    """
    Returns eval results across the current queue run.
    Includes deterministic and qualitative scores per lead.
    """
    return get_eval_results()


@router.get("/patterns")
def read_patterns() -> dict:
    """
    Returns recurring patterns surfaced by the analyzer.
    Which failure modes are appearing most frequently.
    Where agent reasoning is consistently thin.
    """
    return get_patterns()