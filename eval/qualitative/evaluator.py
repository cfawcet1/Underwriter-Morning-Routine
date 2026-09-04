"""
Qualitative evaluator — LLM that scores agent reasoning.
Scores edge case leads where no reference answer exists.
Evaluates reasoning quality against versioned criteria.
Uses MockLLMClient for deterministic scoring in POC.
Replace with AnthropicLLMClient for production eval.
"""
from __future__ import annotations
import re
from typing import Any
from eval.qualitative.prompt import build_evaluator_prompt
from api.services.lead_service import get_lead
from agent.reasoning.mock import MockLLMClient


_llm = MockLLMClient()


def run(lead_id: str, ground_truth: dict) -> dict:
    """
    Runs qualitative eval against a single edge case lead.
    Scores the agent's reasoning against versioned criteria.

    Args:
        lead_id:        The lead identifier.
        ground_truth:   The manifest entry for this lead.

    Returns:
        {
            lead_id:                str,
            track:                  str,
            classification_accurate: bool | None,
            action_appropriate:     bool,
            output_scoped:          bool,
            qualitative_score:      float,
            notes:                  str,
        }
    """
    agent_output = get_lead(lead_id, _llm)

    if not agent_output:
        return _failed(lead_id, "Lead not found in fixture set.")

    prompt = build_evaluator_prompt(lead_id, ground_truth, agent_output)

    # _llm is MockLLMClient in the POC — swap in AnthropicLLMClient for
    # production eval. Both implement complete() and return a response
    # in the same structure, so _parse_judge_response handles either.
    judge_response = _llm.complete(prompt)

    return _parse_judge_response(lead_id, judge_response)


def _parse_judge_response(lead_id: str, response: str) -> dict:
    """
    Parses the CLASSIFICATION/ACTION/SCOPE/UNKNOWN_UNKNOWNS/OVERALL_SCORE
    structure defined in eval/qualitative/prompt.py's response format.
    Works identically whether `response` came from MockLLMClient or a
    real Anthropic completion.
    """
    classification_raw, classification_note = _extract_dimension(response, "CLASSIFICATION")
    action_raw, action_note = _extract_dimension(response, "ACTION")
    scope_raw, scope_note = _extract_dimension(response, "SCOPE")
    unknowns_raw, unknowns_note = _extract_dimension(response, "UNKNOWN_UNKNOWNS")

    if classification_raw not in ("PASS", "FAIL") or \
            action_raw not in ("PASS", "FAIL") or \
            scope_raw not in ("PASS", "FAIL"):
        return _failed(lead_id, f"Could not parse evaluator response: {response!r}")

    score_match = re.search(r"OVERALL_SCORE:\s*([0-9]*\.?[0-9]+)", response)
    qualitative_score = round(float(score_match.group(1)), 2) if score_match else 0.0

    notes = " ".join(n for n in (classification_note, action_note, scope_note) if n)
    if unknowns_raw == "YES" and unknowns_note:
        notes = f"{notes} Unknown unknowns: {unknowns_note}".strip()

    return {
        "lead_id": lead_id,
        "track": "qualitative",
        "classification_accurate": classification_raw == "PASS",
        "action_appropriate": action_raw == "PASS",
        "output_scoped": scope_raw == "PASS",
        "qualitative_score": qualitative_score,
        "notes": notes or "Judge response parsed.",
    }


def _extract_dimension(response: str, label: str) -> tuple[str | None, str]:
    """Extracts a dimension's verdict word and one-sentence explanation."""
    match = re.search(rf"{label}:\s*([A-Z_]+)\s*[—-]?\s*(.*)", response)
    if not match:
        return None, ""
    return match.group(1), match.group(2).strip()


def _failed(lead_id: str, reason: str) -> dict:
    return {
        "lead_id": lead_id,
        "track": "qualitative",
        "classification_accurate": None,
        "action_appropriate": False,
        "output_scoped": False,
        "qualitative_score": 0.0,
        "notes": reason,
    }