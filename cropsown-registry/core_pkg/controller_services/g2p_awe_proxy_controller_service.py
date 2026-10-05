import logging
from typing import Any

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..helpers import AWEClientError, AweHelper
from ..helpers.awe_status_summary import parse_awe_request_status_summary
from ..models import G2PIntakeFormSubmission, G2PRegisterChangeRequest
from ..services.g2p_register_change_request_service import G2PRegisterChangeRequestService
from ..models.enum import ApprovalStatusEnum
from ..schemas.awe_proxy import (
    ClaimAweTaskRequestPayload,
    GetAweRequestEventsRequestPayload,
    GetAweRequestRequestPayload,
    ListMyAweTasksPayload,
    ListTasksForRequestPayload,
    MyAweTaskStatsRequestPayload,
    SubmitAweTaskDecisionRequestPayload,
)

_logger = logging.getLogger("g2p-awe-proxy-controller-service")

REGISTRY_CHANGE_REQUEST_ARTIFACT = "registry.change_request"
REGISTRY_INTAKE_FORM_ARTIFACT = "registry.intake_form"

_TERMINAL_APPROVAL_STATUSES = frozenset(
    {
        ApprovalStatusEnum.APPROVED.value,
        ApprovalStatusEnum.REJECTED.value,
    }
)


class G2PAweProxyControllerService(BaseService):
    @staticmethod
    def _wrap_awe_error(exc: AWEClientError) -> G2PRegistryException:
        if exc.error_code == "AWE-007":
            return G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_INVALID_STATE_TRANSITION.value[1],
                message=exc.message,
            )
        return G2PRegistryException(
            code=G2PRegistryErrorCodes.AWE_REQUEST_FAILED.value[1],
            message=f"{G2PRegistryErrorCodes.AWE_REQUEST_FAILED.value[0]}: {exc.message}",
        )

    @staticmethod
    def _invalid_state(message: str) -> G2PRegistryException:
        return G2PRegistryException(
            code=G2PRegistryErrorCodes.AWE_INVALID_STATE_TRANSITION.value[1],
            message=message,
        )

    async def list_my_tasks(
        self,
        payload: ListMyAweTasksPayload,
        *,
        bearer_token: str,
    ) -> dict[str, Any]:
        try:
            return await AweHelper.get_component().list_my_tasks(
                bearer_token,
                request_id=payload.request_id,
                status=payload.status,
                artifact_type=payload.artifact_type,
                policy_key=payload.policy_key,
                search_text=payload.search_text,
                page=payload.page,
                page_size=payload.page_size,
            )
        except AWEClientError as exc:
            raise self._wrap_awe_error(exc) from exc

    async def list_tasks_for_request(
        self,
        payload: ListTasksForRequestPayload,
        *,
        bearer_token: str,
    ) -> dict[str, Any]:
        try:
            return await AweHelper.get_component().list_tasks_for_request(
                bearer_token,
                request_id=payload.request_id,
                page_size=payload.page_size,
            )
        except AWEClientError as exc:
            raise self._wrap_awe_error(exc) from exc

    async def my_task_stats(
        self,
        payload: MyAweTaskStatsRequestPayload,
        *,
        bearer_token: str,
    ) -> dict[str, Any]:
        try:
            return await AweHelper.get_component().my_task_stats(
                bearer_token,
                status=payload.status,
            )
        except AWEClientError as exc:
            raise self._wrap_awe_error(exc) from exc

    async def submit_task_decision(
        self,
        payload: SubmitAweTaskDecisionRequestPayload,
        *,
        bearer_token: str,
    ) -> dict[str, Any]:
        await self._validate_artifact_in_flight(payload.artifact_type, payload.artifact_id, payload.current_stage)
        await self._validate_change_request_sequence_for_decision(
            payload.artifact_type,
            payload.artifact_id,
            payload.action,
        )

        try:
            return await AweHelper.get_component().submit_decision(
                bearer_token,
                payload.task_id,
                action=payload.action,
                comment=payload.comment,
                attachments_ref=payload.attachments_ref,
            )
        except AWEClientError as exc:
            raise self._wrap_awe_error(exc) from exc

    async def _validate_change_request_sequence_for_decision(
        self,
        artifact_type: str,
        artifact_id: str,
        action: str,
    ) -> None:
        if artifact_type != REGISTRY_CHANGE_REQUEST_ARTIFACT or action != "approve":
            return

        sequence_check = await G2PRegisterChangeRequestService.get_component().get_change_request_sequence_check(
            artifact_id
        )
        if sequence_check.approval_decision_blocked:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[1],
                message="There are earlier pending change requests for this record",
            )

    async def claim_task(
        self,
        payload: ClaimAweTaskRequestPayload,
        *,
        bearer_token: str,
    ) -> dict[str, Any]:
        try:
            return await AweHelper.get_component().claim_task(bearer_token, payload.task_id)
        except AWEClientError as exc:
            raise self._wrap_awe_error(exc) from exc

    async def get_request(
        self,
        payload: GetAweRequestRequestPayload,
        *,
        bearer_token: str,
    ) -> dict[str, Any]:
        try:
            return await AweHelper.get_component().get_request(bearer_token, payload.request_id)
        except AWEClientError as exc:
            raise self._wrap_awe_error(exc) from exc

    async def get_request_events(
        self,
        payload: GetAweRequestEventsRequestPayload,
        *,
        bearer_token: str,
    ) -> list[dict[str, Any]]:
        try:
            return await AweHelper.get_component().get_request_events(
                bearer_token, payload.request_id
            )
        except AWEClientError as exc:
            raise self._wrap_awe_error(exc) from exc

    async def _validate_artifact_in_flight(
        self,
        artifact_type: str,
        artifact_id: str,
        client_stage: int,
    ) -> None:
        """Validate registry artifact state from DB before calling AWE."""
        approval_status, awe_request_status_summary, awe_request_id = (
            await self._load_artifact_decision_context(artifact_type, artifact_id)
        )

        if approval_status in _TERMINAL_APPROVAL_STATUSES:
            raise self._invalid_state(
                f"Record is already '{approval_status}' — cannot decide"
            )

        if not awe_request_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_WEBHOOK_UNSUPPORTED_ARTIFACT.value[1],
                message=(
                    f"{G2PRegistryErrorCodes.AWE_WEBHOOK_UNSUPPORTED_ARTIFACT.value[0]}: "
                    f"no AWE request for artifact {artifact_type}/{artifact_id}"
                ),
            )

        _, stored_stage = parse_awe_request_status_summary(awe_request_status_summary)
        if stored_stage is not None and stored_stage > client_stage:
            raise self._invalid_state(
                f"Request advanced to stage {stored_stage} — cannot decide on stage {client_stage}"
            )

    async def _load_artifact_decision_context(
        self,
        artifact_type: str,
        artifact_id: str,
    ) -> tuple[str | None, str | None, str | None]:
        """Return ``(approval_status, awe_request_status_summary, awe_request_id)``."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            if artifact_type == REGISTRY_CHANGE_REQUEST_ARTIFACT:
                row = (
                    await session.execute(
                        select(
                            G2PRegisterChangeRequest.approval_status,
                            G2PRegisterChangeRequest.awe_request_status_summary,
                            G2PRegisterChangeRequest.awe_request_id,
                        ).where(
                            G2PRegisterChangeRequest.change_request_id == artifact_id
                        )
                    )
                ).one_or_none()
                if row is None:
                    raise G2PRegistryException(
                        code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[1],
                        message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[0],
                    )
                return row.approval_status, row.awe_request_status_summary, row.awe_request_id

            if artifact_type == REGISTRY_INTAKE_FORM_ARTIFACT:
                row = (
                    await session.execute(
                        select(
                            G2PIntakeFormSubmission.approval_status,
                            G2PIntakeFormSubmission.awe_request_status_summary,
                            G2PIntakeFormSubmission.awe_request_id,
                        ).where(
                            G2PIntakeFormSubmission.submission_id == artifact_id
                        )
                    )
                ).one_or_none()
                if row is None:
                    raise G2PRegistryException(
                        code=G2PRegistryErrorCodes.INTAKE_FORM_NOT_FOUND.value[1],
                        message=G2PRegistryErrorCodes.INTAKE_FORM_NOT_FOUND.value[0],
                    )
                return row.approval_status, row.awe_request_status_summary, row.awe_request_id

        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.AWE_WEBHOOK_UNSUPPORTED_ARTIFACT.value[1],
            message=(
                f"{G2PRegistryErrorCodes.AWE_WEBHOOK_UNSUPPORTED_ARTIFACT.value[0]}: "
                f"{artifact_type}"
            ),
        )
