import logging
from typing import List, Optional, Tuple

from openg2p_fastapi_common.schemas import G2PPaginationRequest, G2PPaginationResponse
from openg2p_fastapi_common.service import BaseService

from ..services import G2PVcConfigurationService
from ..schemas import (
    VcConfigurationData,
    VcConfigurationRequest,
)

_logger = logging.getLogger("g2p-vc-configuration-controller-service")


class G2PVcConfigurationControllerService(BaseService):
    async def get_vc_configuration_for_register(
        self,
        vc_configuration_request: VcConfigurationRequest,
    ) -> Tuple[List[VcConfigurationData], Optional[G2PPaginationResponse]]:
        """Get registry vc configurations for particular register_id."""
        _logger.info("Fetching registry vc configuration through controller service")
        pagination_request = vc_configuration_request.request_body.pagination_request
        current_page, page_size = self._extract_pagination_values(pagination_request)
        payload = vc_configuration_request.request_body.request_payload

        g2p_vc_configuration_service = G2PVcConfigurationService.get_component()
        vc_configuration_data, total_items = (
            await g2p_vc_configuration_service.get_vc_configuration_for_register(
                register_id=payload.register_id,
                current_page=current_page,
                page_size=page_size,
            )
        )
        pagination_response = self._build_pagination_response(
            total_items, page_size, pagination_request
        )
        return vc_configuration_data, pagination_response

    async def get_all_vc_configurations(
        self,
        vc_configuration_request: VcConfigurationRequest,
    ) -> Tuple[List[VcConfigurationData], Optional[G2PPaginationResponse]]:
        """Get all registry vc configurations."""
        _logger.info("Fetching all registry vc configurations through controller service")
        pagination_request = vc_configuration_request.request_body.pagination_request
        current_page, page_size = self._extract_pagination_values(pagination_request)

        g2p_vc_configuration_service = G2PVcConfigurationService.get_component()
        vc_configuration_data, total_items = (
            await g2p_vc_configuration_service.get_all_vc_configurations(
                current_page=current_page,
                page_size=page_size,
            )
        )
        pagination_response = self._build_pagination_response(
            total_items, page_size, pagination_request
        )
        return vc_configuration_data, pagination_response

    async def create_vc_configuration(
        self,
        vc_configuration_request: VcConfigurationRequest,
    ) -> List[VcConfigurationData]:
        """Create registry vc configuration."""
        _logger.info("Create vc configurations through controller service")
        payload = vc_configuration_request.request_body.request_payload
        g2p_vc_configuration_service = G2PVcConfigurationService.get_component()
        return await g2p_vc_configuration_service.create_vc_configuration(
            register_id=payload.register_id,
            vc_mnemonic=payload.vc_mnemonic,
            descriptor_schema=payload.descriptor_schema,
            intake_form_id=payload.intake_form_id,
            data_model_id=payload.data_model_id,
        )

    async def edit_descriptor_schema(
        self,
        vc_configuration_request: VcConfigurationRequest,
    ) -> List[VcConfigurationData]:
        """Edit registry vc configuration."""
        _logger.info("Edit vc configurations through controller service")
        payload = vc_configuration_request.request_body.request_payload
        g2p_vc_configuration_service = G2PVcConfigurationService.get_component()
        return await g2p_vc_configuration_service.edit_descriptor_schema(
            vc_config_id=payload.vc_config_id,
            descriptor_schema=payload.descriptor_schema,
        )

    async def delete_vc_configuration(
        self,
        vc_configuration_request: VcConfigurationRequest,
    ) -> List[VcConfigurationData]:
        """Delete registry vc configuration."""
        _logger.info("Delete vc configurations through controller service")
        payload = vc_configuration_request.request_body.request_payload
        g2p_vc_configuration_service = G2PVcConfigurationService.get_component()
        return await g2p_vc_configuration_service.delete_vc_configuration(
            vc_config_id=payload.vc_config_id,
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
