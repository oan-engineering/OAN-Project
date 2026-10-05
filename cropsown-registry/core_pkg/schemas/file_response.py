from typing import Optional

from openg2p_fastapi_common.schemas import G2PResponse, G2PResponseBody

from .file_payload import (
    ChangeRequestDocumentsData,
    DeleteDocumentsData,
    DocumentsData,
    IntakeFormDocumentsData,
    SectionDocumentsData,
)


class DocumentsResponseBody(G2PResponseBody):
    response_payload: Optional[DocumentsData] = None


class DocumentsResponse(G2PResponse):
    response_body: Optional[DocumentsResponseBody] = None


class DeleteDocumentsResponseBody(G2PResponseBody):
    response_payload: Optional[DeleteDocumentsData] = None


class DeleteDocumentsResponse(G2PResponse):
    response_body: Optional[DeleteDocumentsResponseBody] = None


class ChangeRequestDocumentsResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestDocumentsData] = None


class ChangeRequestDocumentsResponse(G2PResponse):
    response_body: Optional[ChangeRequestDocumentsResponseBody] = None


class IntakeFormDocumentsResponseBody(G2PResponseBody):
    response_payload: Optional[IntakeFormDocumentsData] = None


class IntakeFormDocumentsResponse(G2PResponse):
    response_body: Optional[IntakeFormDocumentsResponseBody] = None


class SectionDocumentsResponseBody(G2PResponseBody):
    response_payload: Optional[SectionDocumentsData] = None


class SectionDocumentsResponse(G2PResponse):
    response_body: Optional[SectionDocumentsResponseBody] = None
