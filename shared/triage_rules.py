"""
Derives the four triage actions from field registry metadata.
Imports from shared.registry — does not duplicate it.
Called by the traverser. Nothing else.
"""
from __future__ import annotations
from typing import Any
from shared.registry import (
    is_producer_editable,
    is_system_owned,
    required_level,
)
from shared.ontology import IncompletenessType


def classify_incompleteness(field_name: str) -> IncompletenessType:
    """
    Maps field metadata to an incompleteness type.
    Contradictory and structurally unknowable conditions are
    detected by the traverser and scanner — not derivable from
    registry metadata alone.
    """
    if is_system_owned(field_name):
        return IncompletenessType.SYSTEM_OWNED
    return IncompletenessType.ABSENT_RETRIEVABLE


def triage_action(field_name: str, value: Any) -> str:
    """
    Returns the correct triage action for a missing field.
    Present fields are validated separately in the traverser.
    """
    if value is not None:
        return "present"

    level = required_level(field_name)

    if is_system_owned(field_name):
        return "auto_fetch"

    if level in ("always", "conditional"):
        return "request_via_email"

    if level == "bind_only":
        return "defer_to_bind"

    return "optional"


def is_blocking(field_name: str, value: Any) -> bool:
    """
    A field blocks quoting if it is missing and required always or
    conditional, and cannot be auto-fetched or deferred.
    """
    if value is not None:
        return False
    action = triage_action(field_name, value)
    return action in ("request_via_email", "auto_fetch")