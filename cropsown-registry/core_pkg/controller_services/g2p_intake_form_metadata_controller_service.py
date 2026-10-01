import logging
from typing import Optional

from openg2p_fastapi_common.schemas import G2PPaginationRequest, G2PPaginationResponse
from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    AddIntakeFormSectionRequestPayload,
    CreateIntakeFormRequestPayload,
    CreateIntakeFormTabRequestPayload,
    DeleteIntakeFormRequestPayload,
    DeleteIntakeFormTabRequestPayload,
    GetAllIntakeFormsRequestPayload,
    GetAllIntakeFormSectionsRequestPayload,
    GetAllIntakeFormTabsRequestPayload,
    GetIntakeFormRequestPayload,
    GetIntakeFormTabRequestPayload,
    IntakeFormDefinitionData,
    IntakeFormIdData,
    IntakeFormRenderedData,
    IntakeFormTabIdData,
    IntakeFormTabSectionIdData,
    IntakeFormUITabData,
    IntakeFormUITabSectionData,
    RemoveIntakeFormSectionRequestPayload,
    RenderIntakeFormRequestPayload,
    UpdateIntakeFormRequestPayload,
    UpdateIntakeFormSectionRequestPayload,
    UpdateIntakeFormTabRequestPayload,
)
from ..services import G2PIntakeFormMetadataService

_logger = logging.getLogger("g2p-intake-form-metadata-controller-service")


class G2PIntakeFormMetadataControllerService(BaseService):
    async def create_intake_form(
        self,
        request_payload: CreateIntakeFormRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[IntakeFormIdData, Optional[G2PPaginationResponse]]:
        response_payload = await G2PIntakeFormMetadataService.get_component().create_intake_form(
            register_id=request_payload.register_id,
            form_mnemonic=request_payload.form_mnemonic,
            form_description=request_payload.form_description,
            number_of_verifications=request_payload.number_of_verifications,
            used_only_in_ingestion_pipeline=request_payload.used_only_in_ingestion_pipeline,
        )
        return response_payload, None

    async def update_intake_form(
        self,
        request_payload: UpdateIntakeFormRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[IntakeFormIdData, Optional[G2PPaginationResponse]]:
        response_payload = await G2PIntakeFormMetadataService.get_component().update_intake_form(
            form_id=request_payload.form_id,
            form_mnemonic=request_payload.form_mnemonic,
            form_description=request_payload.form_description,
            number_of_verifications=request_payload.number_of_verifications,
            used_only_in_ingestion_pipeline=request_payload.used_only_in_ingestion_pipeline,
        )
        return response_payload, None

    async def delete_intake_form(
        self,
        request_payload: DeleteIntakeFormRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[None, Optional[G2PPaginationResponse]]:
        await G2PIntakeFormMetadataService.get_component().delete_intake_form(request_payload.form_id)
        return None, None

    async def get_all_intake_forms(
        self,
        request_payload: GetAllIntakeFormsRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[list[IntakeFormDefinitionData], Optional[G2PPaginationResponse]]:
        current_page, page_size = self._extract_pagination_values(pagination_request)

        response_payload, total_items = await G2PIntakeFormMetadataService.get_component().get_all_intake_forms(
            register_id=request_payload.register_id,
            current_page=current_page,
            page_size=page_size,
            used_only_in_ingestion_pipeline=request_payload.used_only_in_ingestion_pipeline,
        )
        pagination_response = self._build_pagination_response(total_items, page_size, pagination_request)
        return response_payload, pagination_response

    async def get_intake_form(
        self,
        request_payload: GetIntakeFormRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[IntakeFormDefinitionData, Optional[G2PPaginationResponse]]:
        response_payload = await G2PIntakeFormMetadataService.get_component().get_intake_form(request_payload.form_id)
        return response_payload, None

    async def render_intake_form(
        self,
        request_payload: RenderIntakeFormRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[IntakeFormRenderedData, Optional[G2PPaginationResponse]]:
        response_payload = await G2PIntakeFormMetadataService.get_component().render_intake_form(
            form_id=request_payload.form_id,
        )
        return response_payload, None

    async def create_tab(
        self,
        request_payload: CreateIntakeFormTabRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[IntakeFormTabIdData, Optional[G2PPaginationResponse]]:
        response_payload = await G2PIntakeFormMetadataService.get_component().create_tab(
            form_id=request_payload.form_id,
            tab_label=request_payload.tab_label,
            tab_order=request_payload.tab_order,
        )
        return response_payload, None

    async def delete_tab(
        self,
        request_payload: DeleteIntakeFormTabRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[None, Optional[G2PPaginationResponse]]:
        await G2PIntakeFormMetadataService.get_component().delete_tab(request_payload.tab_id)
        return None, None

    async def update_tab(
        self,
        request_payload: UpdateIntakeFormTabRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[IntakeFormTabIdData, Optional[G2PPaginationResponse]]:
        response_payload = await G2PIntakeFormMetadataService.get_component().update_tab(
            tab_id=request_payload.tab_id,
            tab_label=request_payload.tab_label,
            tab_order=request_payload.tab_order,
        )
        return response_payload, None

    async def get_tab(
        self,
        request_payload: GetIntakeFormTabRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[IntakeFormUITabData, Optional[G2PPaginationResponse]]:
        response_payload = await G2PIntakeFormMetadataService.get_component().get_tab(request_payload.tab_id)
        return response_payload, None

    async def get_all_tabs(
        self,
        request_payload: GetAllIntakeFormTabsRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[list[IntakeFormUITabData], Optional[G2PPaginationResponse]]:
        current_page, page_size = self._extract_pagination_values(pagination_request)

        response_payload, total_items = await G2PIntakeFormMetadataService.get_component().get_all_tabs(
            form_id=request_payload.form_id,
            current_page=current_page,
            page_size=page_size,
        )
        pagination_response = self._build_pagination_response(total_items, page_size, pagination_request)
        return response_payload, pagination_response

    async def add_section(
        self,
        request_payload: AddIntakeFormSectionRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[IntakeFormTabSectionIdData, Optional[G2PPaginationResponse]]:
        response_payload = await G2PIntakeFormMetadataService.get_component().add_section(
            tab_id=request_payload.tab_id,
            section_id=request_payload.section_id,
            section_order=request_payload.section_order,
        )
        return response_payload, None

    async def remove_section(
        self,
        request_payload: RemoveIntakeFormSectionRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[None, Optional[G2PPaginationResponse]]:
        await G2PIntakeFormMetadataService.get_component().remove_section(request_payload.tab_section_id)
        return None, None

    async def update_section(
        self,
        request_payload: UpdateIntakeFormSectionRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[IntakeFormTabSectionIdData, Optional[G2PPaginationResponse]]:
        response_payload = await G2PIntakeFormMetadataService.get_component().update_section(
            tab_section_id=request_payload.tab_section_id,
            section_order=request_payload.section_order,
        )
        return response_payload, None

    async def get_all_sections(
        self,
        request_payload: GetAllIntakeFormSectionsRequestPayload,
        pagination_request: Optional[G2PPaginationRequest] = None,
    ) -> tuple[list[IntakeFormUITabSectionData], Optional[G2PPaginationResponse]]:
        current_page, page_size = self._extract_pagination_values(pagination_request)

        response_payload, total_items = await G2PIntakeFormMetadataService.get_component().get_all_sections(
            tab_id=request_payload.tab_id,
            current_page=current_page,
            page_size=page_size,
        )
        pagination_response = self._build_pagination_response(total_items, page_size, pagination_request)
        return response_payload, pagination_response

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
