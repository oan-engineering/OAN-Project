import logging

from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    CreateRegisterSectionMetadataRequest,
    DeleteRegisterSectionMetadataRequest,
    G2PRegisterSectionData,
    GetRegisterSectionMetadataRequest,
    GetRegisterSectionMetadataUISchemaRequest,
    GetRegisterSectionsMetadataRequest,
    RegisterSectionIdData,
    RegisterSectionUISchemaData,
    UpdateRegisterSectionMetadataRequest,
    UpdateRegisterSectionMetadataUISchemaRequest,
)
from ..services import G2PRegisterMetadataService

_logger = logging.getLogger("g2p-register-section-metadata-controller-service")


class G2PRegisterSectionMetadataControllerService(BaseService):
    async def create_section(self, request: CreateRegisterSectionMetadataRequest) -> RegisterSectionIdData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().create_section(
            section_register_id=payload.section_register_id,
            register_id=payload.register_id,
            section_mnemonic=payload.section_mnemonic,
            section_description=payload.section_description,
            documents_required=payload.documents_required,
            no_of_verifications_required=payload.no_of_verifications_required,
            cr_auto_approve_for_bene_portal=payload.cr_auto_approve_for_bene_portal,
            cr_auto_approve_for_agent_portal=payload.cr_auto_approve_for_agent_portal,
            cr_auto_approve_for_staff_portal=payload.cr_auto_approve_for_staff_portal,
            cr_auto_approve_for_partner=payload.cr_auto_approve_for_partner,
            is_list=payload.is_list,
            is_core_section=bool(payload.is_core_section),
            section_weightage=payload.section_weightage,
            section_ui_schema=payload.section_ui_schema,
        )

    async def delete_section(self, request: DeleteRegisterSectionMetadataRequest) -> None:
        payload = request.request_body.request_payload
        await G2PRegisterMetadataService.get_component().delete_section(payload.section_id)
        return None

    async def get_all_sections_brief(self, request: GetRegisterSectionsMetadataRequest) -> list[G2PRegisterSectionData]:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().get_all_sections_brief(
            register_id=payload.register_id,
        )

    async def get_all_sections(self, request: GetRegisterSectionsMetadataRequest) -> tuple[list[G2PRegisterSectionData], int, int]:
        payload = request.request_body.request_payload
        pagination = request.request_body.pagination_request
        current_page = pagination.current_page if pagination else None
        page_size = pagination.page_size if pagination else None
        return await G2PRegisterMetadataService.get_component().get_all_sections(
            register_id=payload.register_id,
            current_page=current_page,
            page_size=page_size,
        )

    async def get_section(self, request: GetRegisterSectionMetadataRequest) -> G2PRegisterSectionData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().get_section(
            section_id=payload.section_id,
            register_id=payload.register_id,
        )

    async def update_section(self, request: UpdateRegisterSectionMetadataRequest) -> RegisterSectionIdData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().update_section(
            section_id=payload.section_id,
            section_register_id=payload.section_register_id,
            section_mnemonic=payload.section_mnemonic,
            section_description=payload.section_description,
            documents_required=payload.documents_required,
            no_of_verifications_required=payload.no_of_verifications_required,
            cr_auto_approve_for_bene_portal=payload.cr_auto_approve_for_bene_portal,
            cr_auto_approve_for_agent_portal=payload.cr_auto_approve_for_agent_portal,
            cr_auto_approve_for_staff_portal=payload.cr_auto_approve_for_staff_portal,
            cr_auto_approve_for_partner=payload.cr_auto_approve_for_partner,
            is_list=payload.is_list,
            is_core_section=payload.is_core_section,
            section_weightage=payload.section_weightage,
        )

    async def update_section_ui_schema(self, request: UpdateRegisterSectionMetadataUISchemaRequest) -> RegisterSectionIdData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().update_section_ui_schema(
            section_id=payload.section_id,
            section_ui_schema=payload.section_ui_schema,
            register_id=payload.register_id,
        )

    async def get_section_ui_schema(self, request: GetRegisterSectionMetadataUISchemaRequest) -> RegisterSectionUISchemaData:
        payload = request.request_body.request_payload
        return await G2PRegisterMetadataService.get_component().get_section_ui_schema(
            section_id=payload.section_id,
            register_id=payload.register_id,
        )
