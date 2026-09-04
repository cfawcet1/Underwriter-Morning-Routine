"""
Feedback collector — captures underwriter decisions as eval signal.
Every override the underwriter makes is a data point.
Did the agent classify correctly? Did the escalation give the UW
what they needed? Was the email edited before sending?
These are the signals that make the next iteration better.
"""
from __future__ import annotations
from typing import Any


def collect(
    overrides: list[dict],
    eval_results: list[dict],
) -> list[dict]:
    """
    Matches underwriter overrides to eval results.
    Annotates eval results with underwriter confirmation signal.

    Args:
        overrides:      List of override payloads from actions route.
        eval_results:   Current eval results from both tracks.

    Returns:
        Annotated eval results with underwriter_confirmed field set.
    """
    override_map = {
        o["lead_id"]: o
        for o in overrides
    }

    for result in eval_results:
        lead_id = result.get("lead_id")
        if lead_id in override_map:
            override = override_map[lead_id]
            result["underwriter_confirmed"] = (
                override.get("confirmed_agent_classification", False)
            )
            result["underwriter_decision"] = override.get("decision")
            result["underwriter_reasoning"] = override.get("reasoning")

    return eval_results