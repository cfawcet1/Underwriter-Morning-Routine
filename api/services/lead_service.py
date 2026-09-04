"""
Lead service — bridge between routes and agent pipeline.
Loads fixtures, runs the pipeline, caches results.
Routes never import from agent directly — they go through here.
"""
from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache
from typing import Any
from shared.schema import Lead
from agent.pipeline import run as pipeline_run
from agent.reasoning.llm_client import LLMClient


FIXTURES_PATH = Path(__file__).parents[2] / "data" / "fixtures"
MANIFEST_PATH = FIXTURES_PATH / "manifest.json"

# In-memory result cache for the current queue run
# Resets on server restart — appropriate for POC
_result_cache: dict[str, dict] = {}
_override_log: list[dict] = []


@lru_cache(maxsize=1)
def _load_manifest() -> dict:
    with MANIFEST_PATH.open() as f:
        return json.load(f)


def _load_fixture(relative_path: str) -> Lead:
    path = FIXTURES_PATH / relative_path
    with path.open() as f:
        data = json.load(f)
    return Lead(**data)


def _all_leads() -> list[Lead]:
    manifest = _load_manifest()
    leads = []
    for lead_id, entry in manifest["fixtures"].items():
        lead = _load_fixture(entry["path"])
        leads.append(lead)
    return leads


def get_queue(llm: LLMClient) -> dict:
    """
    Runs the pipeline against all fixture leads.
    Returns results bucketed by decision state.
    """
    leads = _all_leads()
    buckets: dict[str, list] = {
        "ready_to_quote": [],
        "decline": [],
        "refer": [],
        "conditionally_bindable": [],
    }

    for lead in leads:
        result = _get_or_run(lead, llm)
        state = result.get("decision_state", "refer")
        buckets.get(state, buckets["refer"]).append(result)

    return {
        "buckets": buckets,
        "total": sum(len(v) for v in buckets.values()),
    }


def get_lead(lead_id: str, llm: LLMClient) -> dict | None:
    """Returns the pipeline result for a single lead."""
    leads = _all_leads()
    for lead in leads:
        if lead.lead_id == lead_id:
            return _get_or_run(lead, llm)
    return None


def run_lead(lead_id: str, llm: LLMClient) -> dict | None:
    """Force re-runs the pipeline for a lead — bypasses cache."""
    leads = _all_leads()
    for lead in leads:
        if lead.lead_id == lead_id:
            result = pipeline_run(lead, llm)
            _result_cache[lead_id] = result
            return result
    return None


def record_override(payload: dict) -> dict:
    """Records an underwriter override for eval feedback."""
    _override_log.append(payload)
    return payload


def get_overrides() -> list[dict]:
    return list(_override_log)


def _get_or_run(lead: Lead, llm: LLMClient) -> dict:
    """Returns cached result or runs pipeline."""
    if lead.lead_id not in _result_cache:
        _result_cache[lead.lead_id] = pipeline_run(lead, llm)
    return _result_cache[lead.lead_id]