import logging

from openg2p_fastapi_common.service import BaseService

from openg2p_registry_core.models import G2PRegisterChangeRequest

from ..schemas import (
    ChangeRequestRequest,
    ChangeRequestRequestPayload,
    ChangeRequestResponsePayload,
)
from ..services import G2PChangeRequestCoreService

_logger = logging.getLogger("g2p-change-request-core-controller-service")


class G2PChangeRequestCoreControllerService(BaseService):
    async def create_change_request_for_core_data(
        self,
        change_request_request: ChangeRequestRequest,
        *,
        bearer_token: str | None = None,
        requester_sub: str | None = None,
    ) -> ChangeRequestResponsePayload:
        _logger.info("Creating core-data change request through controller service")
        payload: ChangeRequestRequestPayload = (
            change_request_request.request_body.request_payload
        )

        service = G2PChangeRequestCoreService.get_component()
        created_by = payload.created_by or change_request_request.request_header.sender_app_mnemonic
        g2p_register_change_request: G2PRegisterChangeRequest = (
            await service.create_change_request_for_core_data(
                change_request_request_payload=payload,
                source_partner_id=change_request_request.request_header.sender_app_mnemonic,
                bearer_token=bearer_token,
                requester_sub=requester_sub,
                created_by=created_by,
            )
        )

        return self._build_change_request_response_payload(
            payload, g2p_register_change_request
        )

    async def approve_change_request_for_core_data(
        self, change_request_request: ChangeRequestRequest
    ) -> ChangeRequestResponsePayload:
        payload: ChangeRequestRequestPayload = (
            change_request_request.request_body.request_payload
        )
        _logger.info(
            "Approving core-data change request with change_request_id: %s through controller service",
            payload.change_request_id,
        )

        service = G2PChangeRequestCoreService.get_component()
        g2p_register_change_request: G2PRegisterChangeRequest = (
            await service.approve_change_request_for_core_data(payload.change_request_id)
        )

        return self._build_change_request_response_payload(None, g2p_register_change_request)

    async def reject_change_request_for_core_data(
        self, change_request_request: ChangeRequestRequest
    ) -> ChangeRequestResponsePayload:
        payload: ChangeRequestRequestPayload = (
            change_request_request.request_body.request_payload
        )
        _logger.info(
            "Rejecting core-data change request with change_request_id: %s through controller service",
            payload.change_request_id,
        )

        service = G2PChangeRequestCoreService.get_component()
        g2p_register_change_request: G2PRegisterChangeRequest = (
            await service.reject_change_request_for_core_data(
                payload.change_request_id, payload.rejection_reason
            )
        )

        return self._build_change_request_response_payload(None, g2p_register_change_request)

    def _build_change_request_response_payload(
        self,
        change_request_request_payload: ChangeRequestRequestPayload | None,
        g2p_register_change_request: G2PRegisterChangeRequest,
    ) -> ChangeRequestResponsePayload:
        return ChangeRequestResponsePayload(
            record_name=g2p_register_change_request.record_name,
            register_id=change_request_request_payload.register_id
            if change_request_request_payload
            else g2p_register_change_request.register_id,
            tab_id=g2p_register_change_request.tab_id,
            section_id=change_request_request_payload.section_id
            if change_request_request_payload
            else g2p_register_change_request.section_id,
            section_register_id=change_request_request_payload.section_register_id
            if change_request_request_payload
            else g2p_register_change_request.section_register_id,
            no_of_verifications_required=g2p_register_change_request.no_of_verifications_required,
            no_of_verifications_done=g2p_register_change_request.no_of_verifications_done,
            approval_status=g2p_register_change_request.approval_status,
            change_request_id=g2p_register_change_request.change_request_id,
            internal_record_id=g2p_register_change_request.internal_record_id,
            created_by=g2p_register_change_request.created_by,
            created_at=str(g2p_register_change_request.created_at)
            if g2p_register_change_request.created_at
            else None,
            approved_by=g2p_register_change_request.approved_by,
            approved_at=str(g2p_register_change_request.approved_at)
            if g2p_register_change_request.approved_at
            else None,
        )
