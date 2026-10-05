"""Format and parse ``awe_request_status_summary`` values stored on registry artifacts."""

from __future__ import annotations

import re
from typing import Sequence

_STAGE_SUFFIX_RE = re.compile(r"^(.+)-stage(\d+)$")

# AWE request.status values in lifecycle order (higher = later).
_STATUS_RANK: dict[str, int] = {
    "pending": 0,
    "in_review": 1,
    "approved": 2,
    "rejected": 2,
    "cancelled": 2,
}


def format_awe_request_status_summary(
    status: str | None,
    stage_order: int | None,
) -> str | None:
    """Build summary like ``in_review-stage2`` from request status and stage."""
    if not status:
        return None
    if stage_order is not None:
        return f"{status}-stage{stage_order}"
    return status


def parse_awe_request_status_summary(summary: str | None) -> tuple[str | None, int | None]:
    """Return ``(status, stage_order)`` parsed from a stored summary string."""
    if not summary:
        return None, None
    match = _STAGE_SUFFIX_RE.match(summary.strip())
    if match:
        return match.group(1), int(match.group(2))
    return summary, None


def _pick_status(incoming: str | None, existing: str | None) -> str | None:
    """Keep the later lifecycle status when replaying out-of-order webhook events."""
    if not incoming:
        return existing
    if not existing:
        return incoming
    incoming_rank = _STATUS_RANK.get(incoming, -1)
    existing_rank = _STATUS_RANK.get(existing, -1)
    if incoming_rank >= existing_rank:
        return incoming
    return existing


def resolve_awe_request_status_summary(
    *,
    event_type: str,
    status: str | None,
    stage_order: int | None,
    existing_summary: str | None,
    skip_event_types: frozenset[str] | set[str] | None = None,
) -> str | None:
    """Compute the summary to persist for an AWE webhook event.

    ``stage_completed`` and ``request_created`` are normally skipped by the
    webhook service: the former races with the next ``stage_started``, and the
    latter is seeded when the registry creates the AWE request.
    """
    if skip_event_types and event_type in skip_event_types:
        return existing_summary
    if not status:
        return existing_summary

    existing_status, current_stage = parse_awe_request_status_summary(existing_summary)
    effective_status = _pick_status(status, existing_status)

    if event_type == "stage_started" and stage_order is not None:
        effective_stage = stage_order
    elif stage_order is not None:
        if current_stage is not None and stage_order < current_stage:
            effective_stage = current_stage
        else:
            effective_stage = stage_order
    else:
        effective_stage = current_stage

    return format_awe_request_status_summary(effective_status, effective_stage)


def replay_awe_request_status_summary(
    events: Sequence[tuple[str, str | None, int | None]],
    *,
    skip_event_types: frozenset[str] | set[str] | None = None,
) -> str | None:
    """Derive the summary by replaying webhook events oldest-first."""
    summary: str | None = None
    for event_type, status, stage_order in events:
        summary = resolve_awe_request_status_summary(
            event_type=event_type,
            status=status,
            stage_order=stage_order,
            existing_summary=summary,
            skip_event_types=skip_event_types,
        )
    return summary
