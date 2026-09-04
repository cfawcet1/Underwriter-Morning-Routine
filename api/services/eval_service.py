"""
Eval service — bridge between routes and eval loop.
Runs deterministic and qualitative eval tracks.
Returns results and patterns to the frontend.
Routes never import from eval directly — they go through here.
"""
from __future__ import annotations
from eval.loop import run as eval_run
from eval.results.analyzer import get_patterns as analyze_patterns
from api.services.lead_service import get_overrides


def get_eval_results() -> dict:
    """
    Runs the eval loop against all fixture leads.
    Returns deterministic and qualitative scores.
    """
    overrides = get_overrides()
    results = eval_run(overrides=overrides)
    return results


def get_patterns() -> dict:
    """
    Returns recurring failure mode patterns across queue runs.
    """
    return analyze_patterns()