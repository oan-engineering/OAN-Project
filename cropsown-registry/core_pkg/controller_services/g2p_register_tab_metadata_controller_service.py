import logging

from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    AddRegisterTabSectionRequest,
    CreateRegisterTabRequest,
    DeleteRegisterTabMetadataRequest,
    G2PRegisterUITabData,
    G2PRegisterUITabSectionData,
    GetRegisterTabMetadataListRequest,
    GetRegisterTabMetadataRequest,
    GetRegisterTabSectionsMetadataRequest,
    RegisterTabIdData,
    RegisterTabSectionIdData,
    RemoveRegisterTabSectionRequest,
    UpdateRegisterTabRequest,
    UpdateRegisterTabSectionRequest,
)
from ..services import G2PRegisterMetadataService

_logger = logging.getLogger("g2p-register-tab-metadata-controller-service")


class G2PRegisterTabMetadataControllerService(BaseService):
    async def create_tab(self, request: CreateRegisterTabRequest) -> RegisterTabIdData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().create_tab(
            register_id=payload.register_id,
            tab_label=payload.tab_label,
            tab_order=payload.tab_order,
            is_active=payload.is_active,
        )

    async def delete_tab(self, request: DeleteRegisterTabMetadataRequest) -> None:
        payload = request.request_body.request_payload
        await G2PRegisterMetadataService.get_component().delete_tab(payload.tab_id)
        return None

    async def get_all_tabs(self, request: GetRegisterTabMetadataListRequest) -> tuple[list[G2PRegisterUITabData], int, int]:
        payload = request.request_body.request_payload
        pagination = request.request_body.pagination_request
        current_page = pagination.current_page if pagination else None
        page_size = pagination.page_size if pagination else None
        return await G2PRegisterMetadataService.get_component().get_all_tabs(
            register_id=payload.register_id,
            current_page=current_page,
            page_size=page_size,
        )

    async def get_tab(self, request: GetRegisterTabMetadataRequest) -> G2PRegisterUITabData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().get_tab(payload.tab_id)

    async def update_tab(self, request: UpdateRegisterTabRequest) -> RegisterTabIdData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().update_tab(
            tab_id=payload.tab_id,
            tab_label=payload.tab_label,
            tab_order=payload.tab_order,
            is_active=payload.is_active,
        )

    async def add_section(self, request: AddRegisterTabSectionRequest) -> RegisterTabSectionIdData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().add_tab_section(
            tab_id=payload.tab_id,
            section_id=payload.section_id,
            section_order=payload.section_order,
            register_id=payload.register_id,
        )

    async def get_sections(self, request: GetRegisterTabSectionsMetadataRequest) -> list[G2PRegisterUITabSectionData]:
        payload = request.request_body.request_payload
        pagination = request.request_body.pagination_request
        current_page = pagination.current_page if pagination else None
        page_size = pagination.page_size if pagination else None
        return await G2PRegisterMetadataService.get_component().get_tab_sections(
            tab_id=payload.tab_id,
            current_page=current_page,
            page_size=page_size,
        )

    async def update_section(self, request: UpdateRegisterTabSectionRequest) -> G2PRegisterUITabSectionData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().update_tab_section(
            tab_section_id=payload.tab_section_id,
            section_id=payload.section_id,
            section_order=payload.section_order,
        )

    async def remove_section(self, request: RemoveRegisterTabSectionRequest) -> None:
        payload = request.request_body.request_payload
        await G2PRegisterMetadataService.get_component().remove_tab_section(payload.tab_section_id)
        return None
