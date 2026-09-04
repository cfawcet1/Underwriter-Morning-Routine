"""
Eval loop — orchestrates deterministic and qualitative tracks.
Receives agent output and scores it against ground truth.

Two tracks running in parallel:
    Deterministic — scores clean cases against manifest ground truth.
    Qualitative   — scores edge case reasoning against versioned criteria.

The loop is the only file that knows both tracks exist.
Each track is independent — neither imports from the other.
Underwriter overrides feed into both tracks as signal.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from eval.deterministic import run as deterministic_run
from eval.qualitative.evaluator import run as qualitative_run
from eval.results.store import save_results
from eval.feedback.collector import collect as collect_feedback


MANIFEST_PATH = (
    Path(__file__).parents[1] / "data" / "fixtures" / "manifest.json"
)


def run(overrides: list[dict] | None = None) -> dict:
    """
    Runs both eval tracks against all fixture leads.
    Collects underwriter feedback from overrides if present.
    Saves results to store.
    Returns a structured summary.

    Args:
        overrides: List of underwriter override decisions from
                   api/services/lead_service.get_overrides().
                   Used as feedback signal for both tracks.

    Returns:
        {
            deterministic:  list[dict],  — pass/fail per clean lead
            qualitative:    list[dict],  — reasoning scores per edge lead
            summary:        dict,        — aggregate metrics
        }
    """
    manifest = _load_manifest()

    deterministic_results = []
    qualitative_results = []

    for lead_id, ground_truth in manifest.items():
        difficulty = ground_truth.get("difficulty", "medium")
        archetype = ground_truth.get("archetype", "unknown")

        if difficulty == "easy" or archetype.startswith("clean_"):
            result = deterministic_run(lead_id, ground_truth)
            deterministic_results.append(result)
        else:
            result = qualitative_run(lead_id, ground_truth)
            qualitative_results.append(result)

    # Collect feedback from underwriter overrides
    if overrides:
        collect_feedback(overrides, deterministic_results + qualitative_results)

    # Persist results
    all_results = deterministic_results + qualitative_results
    save_results(all_results)

    return {
        "deterministic": deterministic_results,
        "qualitative": qualitative_results,
        "summary": _summarize(deterministic_results, qualitative_results),
    }


def _load_manifest() -> dict:
    with MANIFEST_PATH.open() as f:
        return json.load(f)["fixtures"]


def _summarize(
    deterministic: list[dict],
    qualitative: list[dict],
) -> dict:
    """
    Produces aggregate metrics across both tracks.
    These are the numbers that appear in the eval dashboard.
    """
    def _score(results: list[dict]) -> dict:
        if not results:
            return {"total": 0, "passed": 0, "pass_rate": 0.0}
        passed = sum(
            1 for r in results
            if r.get("action_appropriate") and r.get("output_scoped")
        )
        return {
            "total": len(results),
            "passed": passed,
            "pass_rate": round(passed / len(results), 2),
        }

    return {
        "deterministic": _score(deterministic),
        "qualitative": _score(qualitative),
        "total_leads": len(deterministic) + len(qualitative),
    }