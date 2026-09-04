"""
Results store — persists eval results with lead id and timestamp.
In POC: in-memory store. Resets on server restart.
In production: persists to database with lead id as partition key.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


_store: list[dict] = []


def save_results(results: list[dict]) -> None:
    """Saves eval results with timestamp."""
    timestamp = datetime.now(timezone.utc).isoformat()
    for result in results:
        _store.append({
            **result,
            "evaluated_at": timestamp,
        })


def get_results() -> list[dict]:
    """Returns all stored eval results."""
    return list(_store)


def get_results_for_lead(lead_id: str) -> list[dict]:
    """Returns all eval results for a specific lead."""
    return [r for r in _store if r.get("lead_id") == lead_id]


def clear() -> None:
    """Clears the store. Used between test runs."""
    _store.clear()