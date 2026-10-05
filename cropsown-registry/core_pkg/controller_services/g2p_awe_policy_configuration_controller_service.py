import logging
from typing import Optional

from openg2p_fastapi_common.schemas import G2PPaginationRequest, G2PPaginationResponse
from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    AwePolicyConfigurationData,
    CreateAwePolicyConfigurationRequestPayload,
    DeleteAwePolicyConfigurationRequestPayload,
    GetAwePolicyConfigurationRequestPayload,
    GetAllAwePolicyConfigurationsRequestPayload,
    UpdateAwePolicyConfigurationRequestPayload,
)
from ..services import G2PAwePolicyConfigurationService

_logger = logging.getLogger("g2p-awe-policy-configuration-controller-service")


class G2PAwePolicyConfigurationControllerService(BaseService):
    async def get_all_awe_policy_configurations(
        self,
        request_payload: GetAllAwePolicyConfigurationsRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[list[AwePolicyConfigurationData], Optional[G2PPaginationResponse]]:
        current_page, page_size = self._extract_pagination_values(pagination_request)

        response_payload, total_items = await G2PAwePolicyConfigurationService.get_component().get_all_awe_policy_configurations(
            current_page=current_page,
            page_size=page_size,
        )
        pagination_response = self._build_pagination_response(total_items, page_size, pagination_request)
        return response_payload, pagination_response

    async def get_awe_policy_configuration(
        self,
        request_payload: GetAwePolicyConfigurationRequestPayload,
    ) -> AwePolicyConfigurationData:
        _logger.info("Fetching AWE policy configuration id=%s", request_payload.awe_policy_config_id)
        rows = await G2PAwePolicyConfigurationService.get_component().get_awe_policy_configuration(
            request_payload.awe_policy_config_id
        )
        return rows[0]

    async def create_awe_policy_configuration(
        self,
        request_payload: CreateAwePolicyConfigurationRequestPayload,
    ) -> AwePolicyConfigurationData:
        _logger.info("Creating AWE policy configuration policy_scope=%s", request_payload.policy_scope)
        rows = await G2PAwePolicyConfigurationService.get_component().create_awe_policy_configuration(
            policy_scope=request_payload.policy_scope.value,
            register_id=request_payload.register_id,
            intake_form_id=request_payload.intake_form_id,
            section_id=request_payload.section_id,
            policy_type=request_payload.policy_type,
            policy_key=request_payload.policy_key,
            context_field_names=request_payload.context_field_names,
        )
        return rows[0]

    async def update_awe_policy_configuration(
        self,
        request_payload: UpdateAwePolicyConfigurationRequestPayload,
    ) -> AwePolicyConfigurationData:
        _logger.info("Updating AWE policy configuration id=%s", request_payload.awe_policy_config_id)
        rows = await G2PAwePolicyConfigurationService.get_component().update_awe_policy_configuration(
            awe_policy_config_id=request_payload.awe_policy_config_id,
            policy_scope=(
                request_payload.policy_scope.value if request_payload.policy_scope is not None else None
            ),
            register_id=request_payload.register_id,
            intake_form_id=request_payload.intake_form_id,
            section_id=request_payload.section_id,
            policy_type=request_payload.policy_type,
            policy_key=request_payload.policy_key,
            context_field_names=request_payload.context_field_names,
        )
        return rows[0]

    async def delete_awe_policy_configuration(
        self,
        request_payload: DeleteAwePolicyConfigurationRequestPayload,
    ) -> None:
        _logger.info("Deleting AWE policy configuration id=%s", request_payload.awe_policy_config_id)
        await G2PAwePolicyConfigurationService.get_component().delete_awe_policy_configuration(
            request_payload.awe_policy_config_id
        )

    def _extract_pagination_values(
        self,
        pagination_request: Optional[G2PPaginationRequest],
    ) -> tuple[Optional[int], Optional[int]]:
        if pagination_request is None:
            return None, None
        return pagination_request.current_page, pagination_request.page_size

    def _build_pagination_response(
        self,
        total_items: int,
        page_size: Optional[int],
        pagination_request: Optional[G2PPaginationRequest],
    ) -> Optional[G2PPaginationResponse]:
        if pagination_request is None:
            return None
        return G2PPaginationResponse(
            number_of_items=total_items,
            number_of_pages=self._calculate_number_of_pages(total_items, page_size),
        )

    def _calculate_number_of_pages(self, total_items: int, page_size: int | None) -> int:
        if total_items <= 0:
            return 0
        if page_size is None or page_size <= 0:
            return 1
        return (total_items + page_size - 1) // page_size
