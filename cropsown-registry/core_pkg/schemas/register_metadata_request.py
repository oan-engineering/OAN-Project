from openg2p_fastapi_common.schemas import G2PRequest, G2PRequestBody

from .register_metadata_payload import (
    AddRegisterTabSectionRequestPayload,
    CreateRegisterSectionMetadataRequestPayload,
    CreateRegisterTabRequestPayload,
    DeleteRegisterSectionMetadataRequestPayload,
    DeleteRegisterTabMetadataRequestPayload,
    GetRegisterSectionMetadataRequestPayload,
    GetRegisterSectionMetadataUISchemaRequestPayload,
    GetRegisterSectionsMetadataRequestPayload,
    GetRegisterTabMetadataListRequestPayload,
    GetRegisterTabMetadataRequestPayload,
    GetRegisterTabSectionsMetadataRequestPayload,
    RemoveRegisterTabSectionRequestPayload,
    UpdateRegisterSectionMetadataRequestPayload,
    UpdateRegisterSectionMetadataUISchemaRequestPayload,
    UpdateRegisterTabRequestPayload,
    UpdateRegisterTabSectionRequestPayload,
)


class CreateRegisterTabRequestBody(G2PRequestBody):
    request_payload: CreateRegisterTabRequestPayload


class CreateRegisterTabRequest(G2PRequest):
    request_body: CreateRegisterTabRequestBody


class DeleteRegisterTabMetadataRequestBody(G2PRequestBody):
    request_payload: DeleteRegisterTabMetadataRequestPayload


class DeleteRegisterTabMetadataRequest(G2PRequest):
    request_body: DeleteRegisterTabMetadataRequestBody


class GetRegisterTabMetadataRequestBody(G2PRequestBody):
    request_payload: GetRegisterTabMetadataRequestPayload


class GetRegisterTabMetadataRequest(G2PRequest):
    request_body: GetRegisterTabMetadataRequestBody


class GetRegisterTabMetadataListRequestBody(G2PRequestBody):
    request_payload: GetRegisterTabMetadataListRequestPayload


class GetRegisterTabMetadataListRequest(G2PRequest):
    request_body: GetRegisterTabMetadataListRequestBody


class UpdateRegisterTabRequestBody(G2PRequestBody):
    request_payload: UpdateRegisterTabRequestPayload


class UpdateRegisterTabRequest(G2PRequest):
    request_body: UpdateRegisterTabRequestBody


class AddRegisterTabSectionRequestBody(G2PRequestBody):
    request_payload: AddRegisterTabSectionRequestPayload


class AddRegisterTabSectionRequest(G2PRequest):
    request_body: AddRegisterTabSectionRequestBody


class GetRegisterTabSectionsMetadataRequestBody(G2PRequestBody):
    request_payload: GetRegisterTabSectionsMetadataRequestPayload


class GetRegisterTabSectionsMetadataRequest(G2PRequest):
    request_body: GetRegisterTabSectionsMetadataRequestBody


class UpdateRegisterTabSectionRequestBody(G2PRequestBody):
    request_payload: UpdateRegisterTabSectionRequestPayload


class UpdateRegisterTabSectionRequest(G2PRequest):
    request_body: UpdateRegisterTabSectionRequestBody


class RemoveRegisterTabSectionRequestBody(G2PRequestBody):
    request_payload: RemoveRegisterTabSectionRequestPayload


class RemoveRegisterTabSectionRequest(G2PRequest):
    request_body: RemoveRegisterTabSectionRequestBody


class CreateRegisterSectionMetadataRequestBody(G2PRequestBody):
    request_payload: CreateRegisterSectionMetadataRequestPayload


class CreateRegisterSectionMetadataRequest(G2PRequest):
    request_body: CreateRegisterSectionMetadataRequestBody


class DeleteRegisterSectionMetadataRequestBody(G2PRequestBody):
    request_payload: DeleteRegisterSectionMetadataRequestPayload


class DeleteRegisterSectionMetadataRequest(G2PRequest):
    request_body: DeleteRegisterSectionMetadataRequestBody


class GetRegisterSectionMetadataRequestBody(G2PRequestBody):
    request_payload: GetRegisterSectionMetadataRequestPayload


class GetRegisterSectionMetadataRequest(G2PRequest):
    request_body: GetRegisterSectionMetadataRequestBody


class GetRegisterSectionsMetadataRequestBody(G2PRequestBody):
    request_payload: GetRegisterSectionsMetadataRequestPayload


class GetRegisterSectionsMetadataRequest(G2PRequest):
    request_body: GetRegisterSectionsMetadataRequestBody


class GetRegisterSectionMetadataUISchemaRequestBody(G2PRequestBody):
    request_payload: GetRegisterSectionMetadataUISchemaRequestPayload


class GetRegisterSectionMetadataUISchemaRequest(G2PRequest):
    request_body: GetRegisterSectionMetadataUISchemaRequestBody


class UpdateRegisterSectionMetadataRequestBody(G2PRequestBody):
    request_payload: UpdateRegisterSectionMetadataRequestPayload


class UpdateRegisterSectionMetadataRequest(G2PRequest):
    request_body: UpdateRegisterSectionMetadataRequestBody


class UpdateRegisterSectionMetadataUISchemaRequestBody(G2PRequestBody):
    request_payload: UpdateRegisterSectionMetadataUISchemaRequestPayload


class UpdateRegisterSectionMetadataUISchemaRequest(G2PRequest):
    request_body: UpdateRegisterSectionMetadataUISchemaRequestBody
