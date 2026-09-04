"""
Lead service — bridge between routes and agent pipeline.
Loads fixtures, runs the pipeline, caches results.
Routes never import from agent directly — they go through here.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from functools import lru_cache
from typing import Any
import httpx
from shared.schema import Lead
from agent.pipeline import run as pipeline_run
from agent.reasoning.llm_client import LLMClient


FIXTURES_PATH = Path(__file__).parents[2] / "data" / "fixtures"
MANIFEST_PATH = FIXTURES_PATH / "manifest.json"
LEADGEN_URL = os.environ.get("LEADGEN_URL", "http://localhost:8002")

# In-memory result cache for the current queue run
# Resets on server restart — appropriate for POC
# Keyed by (lead_id, llm backend name) — a mock-scored eval run and a
# live Anthropic-scored queue run must never share a cache entry.
_result_cache: dict[tuple[str, str], dict] = {}
_override_log: list[dict] = []


def _cache_key(lead_id: str, llm: LLMClient) -> tuple[str, str]:
    return (lead_id, type(llm).__name__)


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


def _bucket_results(results: list[dict]) -> dict:
    """
    Buckets pipeline results for the queue view.

    A lead with an email sent is bucketed under "awaiting_response"
    regardless of its decision_state. decision_state alone isn't a
    reliable bucket key here: it can be "ready_to_quote" even when a
    blocking, page-unaddressed field triggered an email (e.g. a
    missing last_name with no playbook page opinion on it) — that
    lead is not actually ready to quote, it's waiting on the producer.
    """
    buckets: dict[str, list] = {
        "awaiting_response": [],
        "ready_to_quote": [],
        "decline": [],
        "refer": [],
        "conditionally_bindable": [],
    }
    for result in results:
        if result.get("email") is not None:
            buckets["awaiting_response"].append(result)
            continue
        state = result.get("decision_state", "refer")
        buckets.get(state, buckets["refer"]).append(result)

    return {
        "buckets": buckets,
        "total": sum(len(v) for v in buckets.values()),
    }


def get_queue(llm: LLMClient) -> dict:
    """
    Runs the pipeline against all fixture leads.
    Returns results bucketed by decision state.
    """
    leads = _all_leads()
    results = [_get_or_run(lead, llm) for lead in leads]
    return _bucket_results(results)


def generate_live_queue(
    llm: LLMClient,
    count: int = 10,
    seed: int | None = None,
    difficulty: str = "mixed",
) -> dict:
    """
    Pulls a fresh queue from the leadgen service and triages it.

    Additive to get_queue() — the static fixtures stay the eval
    harness's ground truth (manifest.json ties directly to them);
    this is for live development/demo runs against freshly generated
    leads, per leadgen's own stated purpose. Results are not cached —
    each generation is a new queue, not a re-run of a known lead.
    """
    with httpx.Client() as client:
        params: dict[str, Any] = {"count": count, "difficulty": difficulty}
        if seed is not None:
            params["seed"] = seed
        queue_response = client.post(f"{LEADGEN_URL}/queue", params=params)
        queue_response.raise_for_status()
        queue_meta = queue_response.json()

        leads = []
        for lead_id in queue_meta["lead_ids"]:
            lead_response = client.get(f"{LEADGEN_URL}/leads/{lead_id}")
            lead_response.raise_for_status()
            leads.append(Lead(**lead_response.json()))

    results = [pipeline_run(lead, llm) for lead in leads]
    bucketed = _bucket_results(results)
    bucketed["seed"] = queue_meta["seed"]
    bucketed["difficulty"] = queue_meta["difficulty"]
    return bucketed


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
            _result_cache[_cache_key(lead_id, llm)] = result
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
    key = _cache_key(lead.lead_id, llm)
    if key not in _result_cache:
        _result_cache[key] = pipeline_run(lead, llm)
    return _result_cache[key]