import logging
from openg2p_fastapi_common.service import BaseService

from ..services import G2PRegisterVerificationService
from ..schemas import (
    VerificationData, AddVerificationPayload,
    GetVerificationsRequest, AddVerificationRequest,
)
from ..errors import G2PRegistryErrorCodes, G2PRegistryException

_logger = logging.getLogger('g2p-verification-controller-service')


class G2PVerificationControllerService(BaseService):

    async def get_verifications(self, get_verifications_request: GetVerificationsRequest) -> tuple[list[VerificationData], int, int]:
        payload = get_verifications_request.request_body.request_payload
        pagination = get_verifications_request.request_body.pagination_request
        self._validate_pagination_request(pagination)
        _logger.info(
            "Getting verifications through controller service for "
            f"change_request_id={payload.change_request_id}, submission_id={payload.submission_id}"
        )
        verification_service = G2PRegisterVerificationService.get_component()
        verifications_list, total_items = await verification_service.get_verifications(
            change_request_id=payload.change_request_id,
            submission_id=payload.submission_id,
            current_page=pagination.current_page,
            page_size=pagination.page_size,
            sort_by=pagination.sort_by,
            filter_by=pagination.filter_by
        )
        number_of_pages = (total_items + pagination.page_size - 1) // pagination.page_size if total_items > 0 else 0
        return verifications_list, total_items, number_of_pages

    async def add_verification(self, add_verification_request: AddVerificationRequest) -> VerificationData:
        add_verification_payload: AddVerificationPayload = add_verification_request.request_body.request_payload
        _logger.info(
            "Adding verification through controller service for "
            f"change_request_id={add_verification_payload.change_request_id}, "
            f"submission_id={add_verification_payload.submission_id}"
        )
        verification_service = G2PRegisterVerificationService.get_component()
        verification_data: VerificationData = await verification_service.add_verification(add_verification_payload)
        return verification_data

    def _validate_pagination_request(self, pagination):
        if pagination is None:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[1],
                message="pagination_request is required for this endpoint",
            )
