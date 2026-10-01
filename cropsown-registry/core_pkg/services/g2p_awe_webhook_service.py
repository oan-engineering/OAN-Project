from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine

from ..config import Settings
from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..helpers.awe_webhook_signature import verify_awe_webhook_signature
from ..models import G2PAweReqEvent, G2PIntakeFormSubmission, G2PRegisterChangeRequest
from ..models.enum import ApprovalStatusEnum
from ..schemas.awe_webhook import AweWebhookEvent, AweWebhookDecisionResponse
from .g2p_awe_status_reconcile import (
    REGISTRY_CHANGE_REQUEST_ARTIFACT,
    REGISTRY_INTAKE_FORM_ARTIFACT,
    derive_status_summary_from_event_log,
    reconcile_artifact_status_summary as _reconcile_artifact_status_summary,
)
from .g2p_register_change_request_service import G2PRegisterChangeRequestService
from .intake_form_data_service import G2PIntakeFormDataService

_config = Settings.get_config(strict=False)
_logger = logging.getLogger(_config.logging_default_logger_name)

TERMINAL_EVENT_TYPES = frozenset(
    {"request_approved", "request_rejected", "request_cancelled"}
)
SUMMARY_SKIP_EVENT_TYPES = frozenset({"request_approved", "request_rejected"})
# stage_completed for stage N is delivered concurrently with stage_started for N+1;
# applying it can overwrite the summary back to the old stage.


def _try_parse_submission_uuid(artifact_id: str) -> str | None:
    """Return canonical submission UUID string, or None if artifact_id is not a valid UUID."""
    try:
        return str(uuid.UUID(artifact_id))
    except ValueError:
        return None


class G2PAweWebhookService(BaseService):
    async def _upsert_webhook_event_log(
        self,
        session: AsyncSession,
        event: AweWebhookEvent,
    ) -> G2PAweReqEvent:
        log_row = await session.get(G2PAweReqEvent, event.event_id)
        if log_row is None:
            log_row = G2PAweReqEvent(
                event_id=event.event_id,
                event_type=event.event_type,
                request_id=event.request_id,
                artifact_type=event.artifact_type,
                artifact_id=event.artifact_id,
                status=event.status,
                stage_order=event.stage_order,
                actor=event.actor,
                occurred_at=event.occurred_at,
                received_at=datetime.now(),
                applied=False,
                error=None,
            )
            session.add(log_row)
        else:
            log_row.event_type = event.event_type
            log_row.request_id = event.request_id
            log_row.artifact_type = event.artifact_type
            log_row.artifact_id = event.artifact_id
            log_row.status = event.status
            log_row.stage_order = event.stage_order
            log_row.actor = event.actor
            log_row.occurred_at = event.occurred_at
        await session.flush()
        return log_row

    async def handle_decision_webhook(
        self,
        *,
        raw_body: bytes,
        signature_header: str | None,
        timestamp_header: str | None,
        header_event_id: str | None,
    ) -> AweWebhookDecisionResponse:
        import os
        secret = (
            _config.awe_callback_hmac_secret
            or os.environ.get("REGISTRY_STAFF_PORTAL_API_AWE_CALLBACK_HMAC_SECRET")
            or os.environ.get("REGISTRY_CORE_AWE_CALLBACK_HMAC_SECRET")
            or ""
        ).strip()
        verify_awe_webhook_signature(
            secret=secret,
            body=raw_body,
            signature_header=signature_header,
            timestamp_header=timestamp_header,
            tolerance_seconds=_config.awe_webhook_timestamp_tolerance_seconds,
        )

        event = AweWebhookEvent.model_validate(json.loads(raw_body))
        if header_event_id and header_event_id != event.event_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_WEBHOOK_EVENT_ID_MISMATCH.value[1],
                message=G2PRegistryErrorCodes.AWE_WEBHOOK_EVENT_ID_MISMATCH.value[0],
            )

        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            existing = await session.get(G2PAweReqEvent, event.event_id)
            if existing and existing.applied:
                return AweWebhookDecisionResponse(
                    event_id=event.event_id,
                    applied=True,
                    message="duplicate",
                )

            log_row = await self._upsert_webhook_event_log(session, event)

            try:
                if event.event_type in TERMINAL_EVENT_TYPES:
                    await self._apply_terminal_event(event, session)
                log_row.applied = True
                log_row.error = None
                await session.flush()
                if event.event_type not in SUMMARY_SKIP_EVENT_TYPES:
                    await self._update_status_summary(event, session)
            except Exception as exc:
                error_msg = str(exc)[:2000]
                await session.rollback()
                log_row = await self._upsert_webhook_event_log(session, event)
                log_row.applied = False
                log_row.error = error_msg
                await session.commit()
                raise

            await session.commit()
            return AweWebhookDecisionResponse(
                event_id=event.event_id,
                applied=True,
            )

    async def _update_status_summary(self, event: AweWebhookEvent, session: AsyncSession) -> None:
        if event.artifact_type not in (
            REGISTRY_CHANGE_REQUEST_ARTIFACT,
            REGISTRY_INTAKE_FORM_ARTIFACT,
        ):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_WEBHOOK_UNSUPPORTED_ARTIFACT.value[1],
                message=(
                    f"{G2PRegistryErrorCodes.AWE_WEBHOOK_UNSUPPORTED_ARTIFACT.value[0]}: "
                    f"{event.artifact_type}"
                ),
            )
        prior_summary = None
        if event.artifact_type == REGISTRY_CHANGE_REQUEST_ARTIFACT:
            change_request = await self._resolve_change_request(event, session)
            prior_summary = change_request.awe_request_status_summary
        else:
            submission = await self._resolve_intake_form_submission(event, session)
            prior_summary = submission.awe_request_status_summary

        await _reconcile_artifact_status_summary(
            session,
            artifact_type=event.artifact_type,
            artifact_id=event.artifact_id,
        )

        summary = await derive_status_summary_from_event_log(
            session,
            artifact_type=event.artifact_type,
            artifact_id=event.artifact_id,
        )
        if summary is not None and summary != prior_summary:
            _logger.info(
                "AWE summary updated for %s/%s -> %s",
                event.artifact_type,
                event.artifact_id,
                summary,
            )

    async def _apply_terminal_event(self, event: AweWebhookEvent, session) -> None:
        if event.artifact_type == REGISTRY_CHANGE_REQUEST_ARTIFACT:
            await self._apply_terminal_event_for_change_request(event, session)
            return
        if event.artifact_type == REGISTRY_INTAKE_FORM_ARTIFACT:
            await self._apply_terminal_event_for_intake_form_submission(event, session)
            return
        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.AWE_WEBHOOK_UNSUPPORTED_ARTIFACT.value[1],
            message=(
                f"{G2PRegistryErrorCodes.AWE_WEBHOOK_UNSUPPORTED_ARTIFACT.value[0]}: "
                f"{event.artifact_type}"
            ),
        )

    async def _apply_terminal_event_for_change_request(
        self, event: AweWebhookEvent, session
    ) -> None:
        change_request = await self._resolve_change_request(event, session)

        if event.event_type == "request_approved":
            if change_request.approval_status == ApprovalStatusEnum.APPROVED.value:
                return
            cr_service = G2PRegisterChangeRequestService.get_component()
            await cr_service.approve_change_request_from_awe_webhook(
                change_request.change_request_id,
                session,
                approved_by=event.actor,
            )
            return

        if event.event_type == "request_rejected":
            if change_request.approval_status == ApprovalStatusEnum.REJECTED.value:
                return
            if change_request.approval_status != ApprovalStatusEnum.PENDING.value:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_IN_PENDING_STATE.value[1],
                    message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_IN_PENDING_STATE.value[0],
                )
            cr_service = G2PRegisterChangeRequestService.get_component()
            cr_service._set_change_request_approval_state(
                change_request,
                approval_status=ApprovalStatusEnum.REJECTED.value,
                actor_name=event.actor,
                session=session,
            )
            change_request.remarks = "Rejected via AWE approval workflow"
            return

        if event.event_type == "request_cancelled":
            if change_request.approval_status == ApprovalStatusEnum.CANCELLED.value:
                return
            if change_request.approval_status != ApprovalStatusEnum.PENDING.value:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_IN_PENDING_STATE.value[1],
                    message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_IN_PENDING_STATE.value[0],
                )
            cr_service = G2PRegisterChangeRequestService.get_component()
            cr_service._set_change_request_approval_state(
                change_request,
                approval_status=ApprovalStatusEnum.CANCELLED.value,
                actor_name=event.actor,
                session=session,
            )

    async def _apply_terminal_event_for_intake_form_submission(
        self, event: AweWebhookEvent, session
    ) -> None:
        submission = await self._resolve_intake_form_submission(event, session)
        intake_service = G2PIntakeFormDataService.get_component()

        if event.event_type == "request_approved":
            await intake_service.approve_submission_with_session(
                submission.submission_id,
                session,
                approved_by=event.actor,
            )
            await session.commit()
            await intake_service.process_submission_register_ingest(submission.submission_id)
            return

        if event.event_type == "request_rejected":
            submission = await intake_service.reject_submission_with_session(
                submission.submission_id,
                session,
                rejected_by=event.actor,
            )
            submission.remarks = "Rejected via AWE approval workflow"
            return

        if event.event_type == "request_cancelled":
            await intake_service.cancel_submission_with_session(
                submission.submission_id,
                session,
                cancelled_by=event.actor,
            )

    async def _resolve_change_request(
        self, event: AweWebhookEvent, session
    ) -> G2PRegisterChangeRequest:
        change_request = (
            await session.execute(
                select(G2PRegisterChangeRequest).where(
                    G2PRegisterChangeRequest.change_request_id == event.artifact_id
                )
            )
        ).scalar_one_or_none()

        if change_request is None:
            change_request = (
                await session.execute(
                    select(G2PRegisterChangeRequest).where(
                        G2PRegisterChangeRequest.awe_request_id == event.request_id
                    )
                )
            ).scalar_one_or_none()

        if change_request is None:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[0],
            )

        if (
            change_request.awe_request_id
            and change_request.awe_request_id != event.request_id
        ):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_WEBHOOK_REQUEST_MISMATCH.value[1],
                message=G2PRegistryErrorCodes.AWE_WEBHOOK_REQUEST_MISMATCH.value[0],
            )

        return change_request

    async def _resolve_intake_form_submission(
        self, event: AweWebhookEvent, session
    ) -> G2PIntakeFormSubmission:
        submission: G2PIntakeFormSubmission | None = None
        submission_id = _try_parse_submission_uuid(event.artifact_id)
        if submission_id is not None:
            submission = (
                await session.execute(
                    select(G2PIntakeFormSubmission).where(
                        G2PIntakeFormSubmission.submission_id == submission_id
                    )
                )
            ).scalar_one_or_none()
        else:
            _logger.warning(
                "Intake webhook artifact_id is not a valid UUID (%r); "
                "falling back to awe_request_id=%s",
                event.artifact_id,
                event.request_id,
            )

        if submission is None:
            submission = (
                await session.execute(
                    select(G2PIntakeFormSubmission).where(
                        G2PIntakeFormSubmission.awe_request_id == event.request_id
                    )
                )
            ).scalar_one_or_none()

        if submission is None:
            if submission_id is None:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[1],
                    message=(
                        f"{G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[0]}: "
                        f"artifact_id must be a valid UUID, got {event.artifact_id!r}"
                    ),
                )
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INTAKE_FORM_NOT_FOUND.value[1],
                message=(
                    f"{G2PRegistryErrorCodes.INTAKE_FORM_NOT_FOUND.value[0]}: "
                    f"artifact_id={submission_id}, request_id={event.request_id}"
                ),
            )

        if (
            submission.awe_request_id
            and submission.awe_request_id != event.request_id
        ):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_WEBHOOK_REQUEST_MISMATCH.value[1],
                message=G2PRegistryErrorCodes.AWE_WEBHOOK_REQUEST_MISMATCH.value[0],
            )

        return submission
