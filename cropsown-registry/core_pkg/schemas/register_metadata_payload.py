from typing import Optional

from pydantic import BaseModel, ConfigDict


class G2PRegisterUITabData(BaseModel):
    tab_id: str
    register_id: str
    tab_label: str
    tab_order: int = 0
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True, extra="allow")


class G2PRegisterSectionData(BaseModel):
    register_id: str
    section_id: str
    section_register_id: str
    is_core_section: Optional[bool] = False
    section_mnemonic: str
    section_description: Optional[str] = None
    documents_required: bool = False
    no_of_verifications_required: int = 0
    is_list: bool = False
    section_weightage: float = 0.0
    section_ui_schema: Optional[dict] = None
    cr_auto_approve_for_bene_portal: bool = False
    cr_auto_approve_for_agent_portal: bool = False
    cr_auto_approve_for_staff_portal: bool = False
    cr_auto_approve_for_partner: bool = False

    model_config = ConfigDict(from_attributes=True, extra="allow")


class G2PRegisterUITabSectionData(BaseModel):
    tab_section_id: str
    register_id: str
    tab_id: str
    section_id: str
    section_order: int = 0

    model_config = ConfigDict(from_attributes=True, extra="allow")


class RegisterSectionUISchemaData(BaseModel):
    section_id: str
    section_ui_schema: Optional[dict] = None


class RegisterTabIdData(BaseModel):
    tab_id: str


class RegisterSectionIdData(BaseModel):
    section_id: str


class RegisterTabSectionIdData(BaseModel):
    tab_section_id: str


class CreateRegisterTabRequestPayload(BaseModel):
    register_id: str
    tab_label: str
    tab_order: int = 0
    is_active: bool = True


class DeleteRegisterTabMetadataRequestPayload(BaseModel):
    tab_id: str


class GetRegisterTabMetadataRequestPayload(BaseModel):
    tab_id: str


class GetRegisterTabMetadataListRequestPayload(BaseModel):
    register_id: Optional[str] = None


class UpdateRegisterTabRequestPayload(BaseModel):
    tab_id: str
    tab_label: Optional[str] = None
    tab_order: Optional[int] = None
    is_active: Optional[bool] = None


class AddRegisterTabSectionRequestPayload(BaseModel):
    register_id: Optional[str] = None
    tab_id: str
    section_id: str
    section_order: int = 0


class GetRegisterTabSectionsMetadataRequestPayload(BaseModel):
    tab_id: str


class UpdateRegisterTabSectionRequestPayload(BaseModel):
    tab_section_id: str
    section_id: Optional[str] = None
    section_order: Optional[int] = None


class RemoveRegisterTabSectionRequestPayload(BaseModel):
    tab_section_id: str


class CreateRegisterSectionMetadataRequestPayload(BaseModel):
    section_register_id: str
    register_id: str
    section_mnemonic: str
    section_description: Optional[str] = None
    documents_required: bool = False
    no_of_verifications_required: int = 0
    cr_auto_approve_for_bene_portal: bool = False
    cr_auto_approve_for_agent_portal: bool = False
    cr_auto_approve_for_staff_portal: bool = False
    cr_auto_approve_for_partner: bool = False
    is_list: bool = False
    is_core_section: Optional[bool] = False
    section_weightage: float = 0.0
    section_ui_schema: Optional[dict] = None


class DeleteRegisterSectionMetadataRequestPayload(BaseModel):
    section_id: str


class GetRegisterSectionMetadataRequestPayload(BaseModel):
    section_id: str
    register_id: Optional[str] = None


class GetRegisterSectionsMetadataRequestPayload(BaseModel):
    register_id: str


class GetRegisterSectionMetadataUISchemaRequestPayload(BaseModel):
    section_id: str
    register_id: Optional[str] = None


class UpdateRegisterSectionMetadataRequestPayload(BaseModel):
    section_id: str
    section_register_id: Optional[str] = None
    section_mnemonic: Optional[str] = None
    section_description: Optional[str] = None
    documents_required: Optional[bool] = None
    no_of_verifications_required: Optional[int] = None
    cr_auto_approve_for_bene_portal: Optional[bool] = None
    cr_auto_approve_for_agent_portal: Optional[bool] = None
    cr_auto_approve_for_staff_portal: Optional[bool] = None
    cr_auto_approve_for_partner: Optional[bool] = None
    is_list: Optional[bool] = None
    is_core_section: Optional[bool] = None
    section_weightage: Optional[float] = None


class UpdateRegisterSectionMetadataUISchemaRequestPayload(BaseModel):
    section_id: str
    register_id: Optional[str] = None
    section_ui_schema: Optional[dict] = None


__all__ = [
    "AddRegisterTabSectionRequestPayload",
    "CreateRegisterSectionMetadataRequestPayload",
    "CreateRegisterTabRequestPayload",
    "DeleteRegisterSectionMetadataRequestPayload",
    "DeleteRegisterTabMetadataRequestPayload",
    "G2PRegisterSectionData",
    "G2PRegisterUITabData",
    "G2PRegisterUITabSectionData",
    "GetRegisterSectionMetadataRequestPayload",
    "GetRegisterSectionMetadataUISchemaRequestPayload",
    "GetRegisterSectionsMetadataRequestPayload",
    "GetRegisterTabMetadataListRequestPayload",
    "GetRegisterTabMetadataRequestPayload",
    "GetRegisterTabSectionsMetadataRequestPayload",
    "RegisterSectionUISchemaData",
    "RegisterSectionIdData",
    "RegisterTabIdData",
    "RegisterTabSectionIdData",
    "RemoveRegisterTabSectionRequestPayload",
    "UpdateRegisterSectionMetadataRequestPayload",
    "UpdateRegisterSectionMetadataUISchemaRequestPayload",
    "UpdateRegisterTabRequestPayload",
    "UpdateRegisterTabSectionRequestPayload",
]
