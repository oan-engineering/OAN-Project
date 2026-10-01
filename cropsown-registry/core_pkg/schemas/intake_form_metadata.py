

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from openg2p_fastapi_common.schemas import G2PRequest, G2PRequestBody, G2PResponse, G2PResponseBody

from .register_metadata_payload import G2PRegisterSectionData


class IntakeFormDefinitionData(BaseModel):
    form_id: str
    register_id: str
    form_mnemonic: str
    form_description: Optional[str] = None
    number_of_verifications: int = 0
    used_only_in_ingestion_pipeline: bool = False

    model_config = ConfigDict(from_attributes=True, extra="allow")


class IntakeFormUITabData(BaseModel):
    tab_id: str
    form_id: str
    tab_label: str
    tab_order: int = 0

    model_config = ConfigDict(from_attributes=True, extra="allow")


class IntakeFormUITabSectionData(BaseModel):
    tab_section_id: str
    tab_id: str
    section_id: str
    section_order: int = 0

    model_config = ConfigDict(from_attributes=True, extra="allow")


class IntakeFormIdData(BaseModel):
    form_id: str


class IntakeFormTabIdData(BaseModel):
    tab_id: str


class IntakeFormTabSectionIdData(BaseModel):
    tab_section_id: str


class IntakeFormRenderedSectionData(G2PRegisterSectionData):
    tab_section_id: str
    section_order: int


class IntakeFormRenderedTabData(BaseModel):
    tab_id: str
    form_id: str
    tab_label: str
    tab_order: int = 0
    sections: List[IntakeFormRenderedSectionData]

    model_config = ConfigDict(from_attributes=True, extra="allow")


class IntakeFormRenderedData(BaseModel):
    form_id: str
    register_id: str
    form_mnemonic: str
    form_description: Optional[str] = None
    number_of_verifications: int = 0
    used_only_in_ingestion_pipeline: bool = False
    tabs: List[IntakeFormRenderedTabData]

    model_config = ConfigDict(from_attributes=True, extra="allow")


class CreateIntakeFormRequestPayload(BaseModel):
    register_id: str
    form_mnemonic: str
    form_description: Optional[str] = None
    number_of_verifications: int = 0
    used_only_in_ingestion_pipeline: bool = False


class UpdateIntakeFormRequestPayload(BaseModel):
    form_id: str
    form_mnemonic: Optional[str] = None
    form_description: Optional[str] = None
    number_of_verifications: Optional[int] = None
    used_only_in_ingestion_pipeline: Optional[bool] = None


class DeleteIntakeFormRequestPayload(BaseModel):
    form_id: str


class GetAllIntakeFormsRequestPayload(BaseModel):
    register_id: Optional[str] = None
    used_only_in_ingestion_pipeline: Optional[bool] = None


class GetIntakeFormRequestPayload(BaseModel):
    form_id: str


class RenderIntakeFormRequestPayload(BaseModel):
    form_id: str


class CreateIntakeFormTabRequestPayload(BaseModel):
    form_id: str
    tab_label: str
    tab_order: int = 0


class DeleteIntakeFormTabRequestPayload(BaseModel):
    tab_id: str


class UpdateIntakeFormTabRequestPayload(BaseModel):
    tab_id: str
    tab_label: Optional[str] = None
    tab_order: Optional[int] = None


class GetIntakeFormTabRequestPayload(BaseModel):
    tab_id: str


class GetAllIntakeFormTabsRequestPayload(BaseModel):
    form_id: Optional[str] = None


class AddIntakeFormSectionRequestPayload(BaseModel):
    tab_id: str
    section_id: str
    section_order: int = 0


class RemoveIntakeFormSectionRequestPayload(BaseModel):
    tab_section_id: str


class UpdateIntakeFormSectionRequestPayload(BaseModel):
    tab_section_id: str
    section_order: Optional[int] = None


class GetAllIntakeFormSectionsRequestPayload(BaseModel):
    tab_id: Optional[str] = None


class CreateIntakeFormRequestBody(G2PRequestBody):
    request_payload: CreateIntakeFormRequestPayload


class CreateIntakeFormRequest(G2PRequest):
    request_body: CreateIntakeFormRequestBody


class UpdateIntakeFormRequestBody(G2PRequestBody):
    request_payload: UpdateIntakeFormRequestPayload


class UpdateIntakeFormRequest(G2PRequest):
    request_body: UpdateIntakeFormRequestBody


class DeleteIntakeFormRequestBody(G2PRequestBody):
    request_payload: DeleteIntakeFormRequestPayload


class DeleteIntakeFormRequest(G2PRequest):
    request_body: DeleteIntakeFormRequestBody


class GetAllIntakeFormsRequestBody(G2PRequestBody):
    request_payload: GetAllIntakeFormsRequestPayload


class GetAllIntakeFormsRequest(G2PRequest):
    request_body: GetAllIntakeFormsRequestBody


class GetIntakeFormRequestBody(G2PRequestBody):
    request_payload: GetIntakeFormRequestPayload


class GetIntakeFormRequest(G2PRequest):
    request_body: GetIntakeFormRequestBody


class RenderIntakeFormRequestBody(G2PRequestBody):
    request_payload: RenderIntakeFormRequestPayload


class RenderIntakeFormRequest(G2PRequest):
    request_body: RenderIntakeFormRequestBody


class CreateIntakeFormTabRequestBody(G2PRequestBody):
    request_payload: CreateIntakeFormTabRequestPayload


class CreateIntakeFormTabRequest(G2PRequest):
    request_body: CreateIntakeFormTabRequestBody


class DeleteIntakeFormTabRequestBody(G2PRequestBody):
    request_payload: DeleteIntakeFormTabRequestPayload


class DeleteIntakeFormTabRequest(G2PRequest):
    request_body: DeleteIntakeFormTabRequestBody


class UpdateIntakeFormTabRequestBody(G2PRequestBody):
    request_payload: UpdateIntakeFormTabRequestPayload


class UpdateIntakeFormTabRequest(G2PRequest):
    request_body: UpdateIntakeFormTabRequestBody


class GetIntakeFormTabRequestBody(G2PRequestBody):
    request_payload: GetIntakeFormTabRequestPayload


class GetIntakeFormTabRequest(G2PRequest):
    request_body: GetIntakeFormTabRequestBody


class GetAllIntakeFormTabsRequestBody(G2PRequestBody):
    request_payload: GetAllIntakeFormTabsRequestPayload


class GetAllIntakeFormTabsRequest(G2PRequest):
    request_body: GetAllIntakeFormTabsRequestBody


class AddIntakeFormSectionRequestBody(G2PRequestBody):
    request_payload: AddIntakeFormSectionRequestPayload


class AddIntakeFormSectionRequest(G2PRequest):
    request_body: AddIntakeFormSectionRequestBody


class RemoveIntakeFormSectionRequestBody(G2PRequestBody):
    request_payload: RemoveIntakeFormSectionRequestPayload


class RemoveIntakeFormSectionRequest(G2PRequest):
    request_body: RemoveIntakeFormSectionRequestBody


class UpdateIntakeFormSectionRequestBody(G2PRequestBody):
    request_payload: UpdateIntakeFormSectionRequestPayload


class UpdateIntakeFormSectionRequest(G2PRequest):
    request_body: UpdateIntakeFormSectionRequestBody


class GetAllIntakeFormSectionsRequestBody(G2PRequestBody):
    request_payload: GetAllIntakeFormSectionsRequestPayload


class GetAllIntakeFormSectionsRequest(G2PRequest):
    request_body: GetAllIntakeFormSectionsRequestBody


class IntakeFormDefinitionDataResponseBody(G2PResponseBody):
    response_payload: Optional[IntakeFormDefinitionData | IntakeFormIdData] = None


class IntakeFormDefinitionDataResponse(G2PResponse):
    response_body: Optional[IntakeFormDefinitionDataResponseBody] = None


class IntakeFormDefinitionListResponseBody(G2PResponseBody):
    response_payload: Optional[List[IntakeFormDefinitionData]] = None


class IntakeFormDefinitionListResponse(G2PResponse):
    response_body: Optional[IntakeFormDefinitionListResponseBody] = None


class RenderIntakeFormDataResponseBody(G2PResponseBody):
    response_payload: Optional[IntakeFormRenderedData] = None


class RenderIntakeFormDataResponse(G2PResponse):
    response_body: Optional[RenderIntakeFormDataResponseBody] = None


class IntakeFormUITabDataResponseBody(G2PResponseBody):
    response_payload: Optional[IntakeFormUITabData | IntakeFormTabIdData] = None


class IntakeFormUITabDataResponse(G2PResponse):
    response_body: Optional[IntakeFormUITabDataResponseBody] = None


class IntakeFormUITabListResponseBody(G2PResponseBody):
    response_payload: Optional[List[IntakeFormUITabData]] = None


class IntakeFormUITabListResponse(G2PResponse):
    response_body: Optional[IntakeFormUITabListResponseBody] = None


class IntakeFormUITabSectionDataResponseBody(G2PResponseBody):
    response_payload: Optional[IntakeFormUITabSectionData | IntakeFormTabSectionIdData] = None


class IntakeFormUITabSectionDataResponse(G2PResponse):
    response_body: Optional[IntakeFormUITabSectionDataResponseBody] = None


class IntakeFormUITabSectionListResponseBody(G2PResponseBody):
    response_payload: Optional[List[IntakeFormUITabSectionData]] = None


class IntakeFormUITabSectionListResponse(G2PResponse):
    response_body: Optional[IntakeFormUITabSectionListResponseBody] = None


__all__ = [
    "AddIntakeFormSectionRequest",
    "AddIntakeFormSectionRequestBody",
    "AddIntakeFormSectionRequestPayload",
    "CreateIntakeFormRequest",
    "CreateIntakeFormRequestBody",
    "CreateIntakeFormRequestPayload",
    "CreateIntakeFormTabRequest",
    "CreateIntakeFormTabRequestBody",
    "CreateIntakeFormTabRequestPayload",
    "DeleteIntakeFormRequest",
    "DeleteIntakeFormRequestBody",
    "DeleteIntakeFormRequestPayload",
    "DeleteIntakeFormTabRequest",
    "DeleteIntakeFormTabRequestBody",
    "DeleteIntakeFormTabRequestPayload",
    "GetAllIntakeFormsRequest",
    "GetAllIntakeFormsRequestBody",
    "GetAllIntakeFormsRequestPayload",
    "GetAllIntakeFormSectionsRequest",
    "GetAllIntakeFormSectionsRequestBody",
    "GetAllIntakeFormSectionsRequestPayload",
    "GetAllIntakeFormTabsRequest",
    "GetAllIntakeFormTabsRequestBody",
    "GetAllIntakeFormTabsRequestPayload",
    "GetIntakeFormRequest",
    "GetIntakeFormRequestBody",
    "GetIntakeFormRequestPayload",
    "GetIntakeFormTabRequest",
    "IntakeFormRenderedData",
    "IntakeFormRenderedSectionData",
    "IntakeFormRenderedTabData",
    "RenderIntakeFormDataResponse",
    "RenderIntakeFormDataResponseBody",
    "RenderIntakeFormRequest",
    "RenderIntakeFormRequestBody",
    "RenderIntakeFormRequestPayload",
    "GetIntakeFormTabRequestBody",
    "GetIntakeFormTabRequestPayload",
    "IntakeFormDefinitionData",
    "IntakeFormDefinitionDataResponse",
    "IntakeFormDefinitionDataResponseBody",
    "IntakeFormDefinitionListResponse",
    "IntakeFormDefinitionListResponseBody",
    "IntakeFormIdData",
    "IntakeFormTabIdData",
    "IntakeFormTabSectionIdData",
    "IntakeFormUITabData",
    "IntakeFormUITabDataResponse",
    "IntakeFormUITabDataResponseBody",
    "IntakeFormUITabListResponse",
    "IntakeFormUITabListResponseBody",
    "IntakeFormUITabSectionData",
    "IntakeFormUITabSectionDataResponse",
    "IntakeFormUITabSectionDataResponseBody",
    "IntakeFormUITabSectionListResponse",
    "IntakeFormUITabSectionListResponseBody",
    "RemoveIntakeFormSectionRequest",
    "RemoveIntakeFormSectionRequestBody",
    "RemoveIntakeFormSectionRequestPayload",
    "UpdateIntakeFormRequest",
    "UpdateIntakeFormRequestBody",
    "UpdateIntakeFormRequestPayload",
    "UpdateIntakeFormSectionRequest",
    "UpdateIntakeFormSectionRequestBody",
    "UpdateIntakeFormSectionRequestPayload",
    "UpdateIntakeFormTabRequest",
    "UpdateIntakeFormTabRequestBody",
    "UpdateIntakeFormTabRequestPayload",
]
