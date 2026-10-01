from openg2p_fastapi_common.schemas import G2PRequest, G2PRequestBody

from .file_payload import (
    DeleteDocumentsRequestPayload,
    GetChangeRequestDocumentsRequestPayload,
    GetDocumentsRequestPayload,
    GetIntakeFormDocumentsRequestPayload,
    GetSectionDocumentsRequestPayload,
)


class GetDocumentsRequestBody(G2PRequestBody):
    request_payload: GetDocumentsRequestPayload


class GetDocumentsRequest(G2PRequest):
    request_body: GetDocumentsRequestBody


class DeleteDocumentsRequestBody(G2PRequestBody):
    request_payload: DeleteDocumentsRequestPayload


class DeleteDocumentsRequest(G2PRequest):
    request_body: DeleteDocumentsRequestBody


class GetChangeRequestDocumentsRequestBody(G2PRequestBody):
    request_payload: GetChangeRequestDocumentsRequestPayload


class GetChangeRequestDocumentsRequest(G2PRequest):
    request_body: GetChangeRequestDocumentsRequestBody


class GetIntakeFormDocumentsRequestBody(G2PRequestBody):
    request_payload: GetIntakeFormDocumentsRequestPayload


class GetIntakeFormDocumentsRequest(G2PRequest):
    request_body: GetIntakeFormDocumentsRequestBody


class GetSectionDocumentsRequestBody(G2PRequestBody):
    request_payload: GetSectionDocumentsRequestPayload


class GetSectionDocumentsRequest(G2PRequest):
    request_body: GetSectionDocumentsRequestBody
