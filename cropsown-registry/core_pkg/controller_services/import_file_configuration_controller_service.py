import logging
from typing import List, Optional, Tuple

from openg2p_fastapi_common.schemas import G2PPaginationRequest, G2PPaginationResponse
from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    ImportFileConfigurationData,
    ImportFileConfigurationRequest,
)
from ..services import ImportFileConfigurationService

_logger = logging.getLogger("import-file-configuration-controller-service")


class ImportFileConfigurationControllerService(BaseService):
    async def get_import_file_configuration_for_register(
        self, request: ImportFileConfigurationRequest
    ) -> Tuple[List[ImportFileConfigurationData], Optional[G2PPaginationResponse]]:
        _logger.info(
            "Fetching import-file configuration for register through controller service"
        )
        pagination_request = request.request_body.pagination_request
        current_page, page_size = self._extract_pagination_values(pagination_request)
        payload = request.request_body.request_payload

        import_file_configuration_service = ImportFileConfigurationService.get_component()
        import_file_configuration_data, total_items = (
            await import_file_configuration_service.get_import_file_configuration_for_register(
                register_id=payload.register_id,
                current_page=current_page,
                page_size=page_size,
            )
        )
        pagination_response = self._build_pagination_response(
            total_items, page_size, pagination_request
        )
        return import_file_configuration_data, pagination_response

    async def get_all_import_file_configurations(
        self, request: ImportFileConfigurationRequest
    ) -> Tuple[List[ImportFileConfigurationData], Optional[G2PPaginationResponse]]:
        _logger.info("Fetching all import-file configurations through controller service")
        pagination_request = request.request_body.pagination_request
        current_page, page_size = self._extract_pagination_values(pagination_request)

        import_file_configuration_service = ImportFileConfigurationService.get_component()
        import_file_configuration_data, total_items = (
            await import_file_configuration_service.get_all_import_file_configurations(
                current_page=current_page,
                page_size=page_size,
            )
        )
        pagination_response = self._build_pagination_response(
            total_items, page_size, pagination_request
        )
        return import_file_configuration_data, pagination_response

    async def create_import_file_configuration(
        self, request: ImportFileConfigurationRequest
    ) -> List[ImportFileConfigurationData]:
        _logger.info("Creating import-file configuration through controller service")
        payload = request.request_body.request_payload
        import_file_configuration_service = ImportFileConfigurationService.get_component()
        return await import_file_configuration_service.create_import_file_configuration(
            register_id=payload.register_id,
            form_id=payload.form_id,
            data_model_id=payload.data_model_id,
            import_file_template_mnemonic=payload.import_file_template_mnemonic,
            import_file_template_description=payload.import_file_template_description,
        )

    async def update_import_file_configuration(
        self, request: ImportFileConfigurationRequest
    ) -> List[ImportFileConfigurationData]:
        _logger.info("Updating import-file configuration through controller service")
        payload = request.request_body.request_payload
        import_file_configuration_service = ImportFileConfigurationService.get_component()
        return await import_file_configuration_service.update_import_file_configuration(
            import_file_configuration_id=payload.import_file_configuration_id,
            form_id=payload.form_id,
            data_model_id=payload.data_model_id,
            import_file_template_mnemonic=payload.import_file_template_mnemonic,
            import_file_template_description=payload.import_file_template_description,
        )

    async def delete_import_file_configuration(
        self, request: ImportFileConfigurationRequest
    ) -> List[ImportFileConfigurationData]:
        _logger.info("Deleting import-file configuration through controller service")
        payload = request.request_body.request_payload
        import_file_configuration_service = ImportFileConfigurationService.get_component()
        return await import_file_configuration_service.delete_import_file_configuration(
            import_file_configuration_id=payload.import_file_configuration_id,
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
