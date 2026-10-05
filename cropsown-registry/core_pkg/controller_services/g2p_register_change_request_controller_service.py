import logging
from openg2p_fastapi_common.schemas import G2PPaginationResponse
from openg2p_fastapi_common.service import BaseService

from openg2p_registry_core.models import G2PRegisterChangeRequest

from ..services import G2PRegisterChangeRequestService, G2PRegisterVerificationService
from ..schemas.change_request import (
    ChangeRequestRequest, ChangeRequestRequestPayload, ChangeRequestResponsePayload,
    NumberOfPendingChangeRequestsData, NumberOfCrossRegisterChangesData,
    CrossRegisterChangeRequestData, ChangeRequestData,
    ChangeRequestSequenceCheckData,
    VerificationData, AddVerificationPayload,
    GetNumberOfPendingChangeRequestsRequest, GetNumberOfCrossRegisterChangesRequest,
    GetCrossRegisterChangesRequest,
    GetChangeRequestsRequest, GetChangeRequestRequest,
    CheckChangeRequestSequenceRequest,
    GetVerificationsRequest, AddVerificationRequest,
    GetChangeRequestSummaryDataRequest, ChangeRequestSummaryData,
    SearchChangeRequestRequest, ChangeRequestSearchResultData
)

_logger = logging.getLogger('g2p-register-change_request-controller-service')


class G2PRegisterChangerequestControllerService(BaseService):

    async def create_change_request(
        self,
        change_request_request: ChangeRequestRequest,
        *,
        bearer_token: str | None = None,
        requester_sub: str | None = None,
    ) -> ChangeRequestResponsePayload:
        _logger.info("Creating change request through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        change_request_request_payload: ChangeRequestRequestPayload = change_request_request.request_body.request_payload
        created_by = change_request_request_payload.created_by or change_request_request.request_header.sender_app_mnemonic

        g2p_register_change_request: G2PRegisterChangeRequest = await service.create_change_request(
            change_request_request_payload=change_request_request_payload,
            source_partner_id=change_request_request.request_header.sender_app_mnemonic,
            created_by=created_by,
            bearer_token=bearer_token,
            requester_sub=requester_sub,
        )

        change_request_response_payload: ChangeRequestResponsePayload = self._build_change_request_response_payload(change_request_request_payload, g2p_register_change_request)

        return change_request_response_payload

    async def approve_change_request(self, change_request_request: ChangeRequestRequest) -> ChangeRequestResponsePayload:
        change_request_id = change_request_request.request_body.request_payload.change_request_id
        approved_by = (
            change_request_request.request_body.request_payload.approved_by
            or change_request_request.request_header.sender_app_mnemonic
        )
        _logger.info(f"Approving change request with change_request_id: {change_request_id} through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        g2p_register_change_request: G2PRegisterChangeRequest = await service.approve_change_request(
            change_request_id,
            approved_by=approved_by,
        )
        change_request_response_payload: ChangeRequestResponsePayload = self._build_change_request_response_payload(None, g2p_register_change_request)
        return change_request_response_payload

    async def reject_change_request(self, change_request_request: ChangeRequestRequest) -> ChangeRequestResponsePayload:
        change_request_id = change_request_request.request_body.request_payload.change_request_id
        rejection_reason: str = getattr(change_request_request.request_body.request_payload, 'rejection_reason', None)
        rejected_by = (
            change_request_request.request_body.request_payload.approved_by
            or change_request_request.request_header.sender_app_mnemonic
        )
        _logger.info(f"Rejecting change request with change_request_id: {change_request_id} through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        g2p_register_change_request: G2PRegisterChangeRequest = await service.reject_change_request(
            change_request_id,
            rejection_reason,
            rejected_by=rejected_by,
        )
        change_request_response_payload: ChangeRequestResponsePayload = self._build_change_request_response_payload(None, g2p_register_change_request)
        return change_request_response_payload

    async def get_number_of_pending_change_requests(self, get_number_of_pending_change_requests_request: GetNumberOfPendingChangeRequestsRequest) -> NumberOfPendingChangeRequestsData:
        subject_register_id = get_number_of_pending_change_requests_request.request_body.request_payload.subject_register_id
        subject_record_id = get_number_of_pending_change_requests_request.request_body.request_payload.subject_record_id
        tab_id = get_number_of_pending_change_requests_request.request_body.request_payload.tab_id
        _logger.info(f"Getting number of pending change requests for subject_register_id: {subject_register_id}, subject_record_id: {subject_record_id}, tab_id: {tab_id} through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        number_of_pending_change_requests_data: NumberOfPendingChangeRequestsData = await service.get_number_of_pending_change_requests(subject_register_id, subject_record_id, tab_id)
        return number_of_pending_change_requests_data

    async def get_number_of_cross_register_changes(self, get_number_of_cross_register_changes_request: GetNumberOfCrossRegisterChangesRequest) -> NumberOfCrossRegisterChangesData:
        subject_register_id = get_number_of_cross_register_changes_request.request_body.request_payload.subject_register_id
        subject_record_id = get_number_of_cross_register_changes_request.request_body.request_payload.subject_record_id
        _logger.info(f"Getting number of cross-register changes for subject_register_id: {subject_register_id}, subject_record_id: {subject_record_id} through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        number_of_cross_register_changes_data: NumberOfCrossRegisterChangesData = await service.get_number_of_cross_register_changes(subject_register_id, subject_record_id)
        return number_of_cross_register_changes_data

    async def get_cross_register_changes(self, get_cross_register_changes_request: GetCrossRegisterChangesRequest) -> list[CrossRegisterChangeRequestData]:
        subject_register_id = get_cross_register_changes_request.request_body.request_payload.subject_register_id
        subject_record_id = get_cross_register_changes_request.request_body.request_payload.subject_record_id
        _logger.info(f"Getting cross-register changes for subject_register_id: {subject_register_id}, subject_record_id: {subject_record_id} through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        cross_register_changes: list[CrossRegisterChangeRequestData] = await service.get_cross_register_changes(subject_register_id, subject_record_id)
        return cross_register_changes

    async def get_change_requests(
        self,
        get_change_requests_request: GetChangeRequestsRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> tuple[list[dict], G2PPaginationResponse]:
        payload = get_change_requests_request.request_body.request_payload
        pagination = get_change_requests_request.request_body.pagination_request
        subject_register_id = payload.subject_register_id
        subject_record_id = payload.subject_record_id
        tab_id = payload.tab_id
        _logger.info(f"Getting change requests for subject_register_id: {subject_register_id}, subject_record_id: {subject_record_id}, tab_id: {tab_id} through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        # Use flattened version to return change_payload fields at root level
        change_requests_list, total_items = await service.get_change_requests_flattened(
            subject_register_id,
            subject_record_id,
            tab_id,
            pagination.current_page,
            pagination.page_size,
            pagination.sort_by,
            pagination.filter_by,
            policy_mnemonics=policy_mnemonics,
        )
        pagination_response = self._build_pagination_response(total_items, pagination.page_size)
        return change_requests_list, pagination_response

    async def get_change_request(
        self,
        get_change_request_request: GetChangeRequestRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> ChangeRequestData:
        change_request_id = get_change_request_request.request_body.request_payload.change_request_id
        _logger.info(f"Getting change request for change_request_id: {change_request_id} through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        change_request_data: ChangeRequestData = await service.get_change_request(
            change_request_id,
            policy_mnemonics=policy_mnemonics,
        )
        return change_request_data

    async def check_change_request_sequence(
        self, check_change_request_sequence_request: CheckChangeRequestSequenceRequest
    ) -> ChangeRequestSequenceCheckData:
        change_request_id = (
            check_change_request_sequence_request.request_body.request_payload.change_request_id
        )
        _logger.info(
            "Checking change request sequence for change_request_id: %s through controller service",
            change_request_id,
        )
        service = G2PRegisterChangeRequestService.get_component()
        return await service.get_change_request_sequence_check(change_request_id)

    def _build_change_request_response_payload(self, change_request_request_payload: ChangeRequestRequestPayload, g2p_register_change_request: G2PRegisterChangeRequest) -> ChangeRequestResponsePayload:
        return ChangeRequestResponsePayload(
            record_name=g2p_register_change_request.record_name,
            register_id=change_request_request_payload.register_id if change_request_request_payload else g2p_register_change_request.register_id,
            tab_id=g2p_register_change_request.tab_id,
            section_id=change_request_request_payload.section_id if change_request_request_payload else g2p_register_change_request.section_id,
            section_register_id=change_request_request_payload.section_register_id if change_request_request_payload else g2p_register_change_request.section_register_id,
            no_of_verifications_required=g2p_register_change_request.no_of_verifications_required,
            no_of_verifications_done=g2p_register_change_request.no_of_verifications_done,
            approval_status=g2p_register_change_request.approval_status,
            change_request_id=g2p_register_change_request.change_request_id,
            internal_record_id=g2p_register_change_request.internal_record_id,
            created_by=g2p_register_change_request.created_by,
            created_at=str(g2p_register_change_request.created_at) if g2p_register_change_request.created_at else None,
            approved_by=g2p_register_change_request.approved_by,
            approved_at=str(g2p_register_change_request.approved_at) if g2p_register_change_request.approved_at else None,
            awe_request_id=g2p_register_change_request.awe_request_id,
            awe_request_status_summary=g2p_register_change_request.awe_request_status_summary,
        )

    async def get_verifications_for_change_request(self, get_verifications_request: GetVerificationsRequest) -> tuple[list[VerificationData], G2PPaginationResponse]:
        # Deprecated wrapper.
        # NOTE: Migrate clients to /verifications/get_verifications directly.
        payload = get_verifications_request.request_body.request_payload
        pagination = get_verifications_request.request_body.pagination_request
        change_request_id = payload.change_request_id
        _logger.info(f"Getting verifications for change_request_id: {change_request_id} through controller service")
        verification_service = G2PRegisterVerificationService.get_component()
        verifications_list, total_items = await verification_service.get_verifications(
            change_request_id=change_request_id,
            submission_id=None,
            current_page=pagination.current_page,
            page_size=pagination.page_size,
            sort_by=pagination.sort_by,
            filter_by=pagination.filter_by,
        )
        pagination_response = self._build_pagination_response(total_items, pagination.page_size)
        return verifications_list, pagination_response

    async def add_verification_for_change_request(self, add_verification_request: AddVerificationRequest) -> VerificationData:
        # Deprecated wrapper.
        # NOTE: Migrate clients to /verifications/add_verification directly.
        add_verification_payload: AddVerificationPayload = add_verification_request.request_body.request_payload
        _logger.info(f"Adding verification for change_request_id: {add_verification_payload.change_request_id} through controller service")
        verification_service = G2PRegisterVerificationService.get_component()
        verification_data: VerificationData = await verification_service.add_verification(add_verification_payload)
        return verification_data

    async def get_change_request_summary_data(
        self,
        get_change_request_summary_data_request: GetChangeRequestSummaryDataRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> ChangeRequestSummaryData:
        _logger.info("Fetching change_request summary data through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        change_request_summary_data: ChangeRequestSummaryData = await service.get_change_request_summary_data(
            policy_mnemonics=policy_mnemonics,
        )
        return change_request_summary_data
    
    async def search_in_change_request(
        self,
        search_change_request_request: SearchChangeRequestRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> tuple[list[ChangeRequestSearchResultData], G2PPaginationResponse]:
        pagination = search_change_request_request.request_body.pagination_request
        _logger.info(f"Searching in change requests with search_text: {pagination.search_text} through controller service")
        service = G2PRegisterChangeRequestService.get_component()
        search_results_list, total_items = await service.search_in_change_request(
            pagination.search_text,
            pagination.current_page,
            pagination.page_size,
            pagination.sort_by,
            pagination.filter_by,
            policy_mnemonics=policy_mnemonics,
        )
        pagination_response = self._build_pagination_response(total_items, pagination.page_size)
        return search_results_list, pagination_response

    def _build_pagination_response(self, total_items: int, page_size: int) -> G2PPaginationResponse:
        return G2PPaginationResponse(
            number_of_items=total_items,
            number_of_pages=self._calculate_number_of_pages(total_items, page_size),
        )

    def _calculate_number_of_pages(self, total_items: int, page_size: int) -> int:
        if total_items <= 0:
            return 0
        if page_size <= 0:
            return 1
        return (total_items + page_size - 1) // page_size
