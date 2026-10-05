"""Reconcile ``awe_request_status_summary`` from the webhook event log.

Kept separate from ``g2p_awe_webhook_service`` to avoid circular imports with
change-request and intake-form services.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..helpers.awe_status_summary import replay_awe_request_status_summary
from ..models import G2PAweReqEvent, G2PIntakeFormSubmission, G2PRegisterChangeRequest

REGISTRY_CHANGE_REQUEST_ARTIFACT = "registry.change_request"
REGISTRY_INTAKE_FORM_ARTIFACT = "registry.intake_form"

SUMMARY_SKIP_UPDATE_EVENT_TYPES = frozenset({"stage_completed", "request_created"})


async def derive_status_summary_from_event_log(
    session: AsyncSession,
    *,
    artifact_type: str,
    artifact_id: str,
) -> str | None:
    """Replay applied webhook events so concurrent deliveries cannot regress stage."""
    rows = (
        await session.execute(
            select(
                G2PAweReqEvent.event_type,
                G2PAweReqEvent.status,
                G2PAweReqEvent.stage_order,
            )
            .where(
                G2PAweReqEvent.artifact_type == artifact_type,
                G2PAweReqEvent.artifact_id == artifact_id,
                G2PAweReqEvent.applied.is_(True),
            )
            .order_by(G2PAweReqEvent.occurred_at, G2PAweReqEvent.received_at)
        )
    ).all()
    return replay_awe_request_status_summary(
        rows,
        skip_event_types=SUMMARY_SKIP_UPDATE_EVENT_TYPES,
    )


async def reconcile_artifact_status_summary(
    session: AsyncSession,
    *,
    artifact_type: str,
    artifact_id: str,
) -> None:
    """Refresh stored summary from the webhook event log (e.g. on artifact read)."""
    summary = await derive_status_summary_from_event_log(
        session,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
    )
    if summary is None:
        return

    if artifact_type == REGISTRY_CHANGE_REQUEST_ARTIFACT:
        change_request = (
            await session.execute(
                select(G2PRegisterChangeRequest).where(
                    G2PRegisterChangeRequest.change_request_id == artifact_id
                )
            )
        ).scalar_one_or_none()
        if change_request is None or change_request.awe_request_status_summary == summary:
            return
        change_request.awe_request_status_summary = summary
        session.add(change_request)
        return

    if artifact_type == REGISTRY_INTAKE_FORM_ARTIFACT:
        submission = (
            await session.execute(
                select(G2PIntakeFormSubmission).where(
                    G2PIntakeFormSubmission.submission_id == artifact_id
                )
            )
        ).scalar_one_or_none()
        if submission is None or submission.awe_request_status_summary == summary:
            return
        submission.awe_request_status_summary = summary
        session.add(submission)
