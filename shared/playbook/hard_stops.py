"""
Deterministic hard stops derived from the FigJam electrical flow.
These fire before any other reasoning — no LLM, no traversal.
Tier 1 broker exception noted in README Known Limitations — deferred.
"""
from __future__ import annotations
from typing import Any
from agent.ontology import HardStop


INELIGIBLE_PANELS = {
    "Federal Pacific",
    "Stab-Lok",
    "Zinsco",
    "Challenger",
}


def scan(fields: dict[str, Any]) -> list[HardStop]:
    """
    Returns a list of hard stops found in the lead fields.
    Empty list means no hard stops — proceed to traversal.
    """
    stops: list[HardStop] = []

    panel = fields.get("electrical_panel_brand")
    if panel in INELIGIBLE_PANELS:
        stops.append(HardStop(
            field_name="electrical_panel_brand",
            value=panel,
            reason=f"{panel} electrical panels are ineligible. "
                   f"Replacement required prior to binding."
        ))

    knob_and_tube = fields.get("has_knob_and_tube_wiring")
    year_built = fields.get("year_built")

    # Apply missingDefault from field registry:
    # assume knob and tube present if year_built < 1950
    if knob_and_tube is None and year_built is not None and year_built < 1950:
        knob_and_tube = True

    if knob_and_tube is True:
        stops.append(HardStop(
            field_name="has_knob_and_tube_wiring",
            value=True,
            reason="Knob and tube wiring is ineligible. "
                   "Full rewire required prior to binding."
        ))

    return stops
