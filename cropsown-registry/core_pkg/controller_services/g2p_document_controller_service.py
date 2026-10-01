import logging
from typing import List

from fastapi import UploadFile
from openg2p_fastapi_common.service import BaseService

from ..services import G2PDocumentService
from ..schemas import (
    ChangeRequestDocumentsData,
    DeleteDocumentsData,
    DeleteDocumentsRequest,
    DocumentsData,
    GetChangeRequestDocumentsRequest,
    GetDocumentsRequest,
    GetIntakeFormDocumentsRequest,
    GetSectionDocumentsRequest,
    IntakeFormDocumentsData,
    SectionDocumentsData,
    UploadDocumentsRequestPayload,
)

_logger = logging.getLogger('g2p-document-controller-service')


class G2PDocumentControllerService(BaseService):
    """
    Controller service for document operations; delegates to G2PDocumentService.
    """

    @property
    def document_service(self) -> G2PDocumentService:
        return G2PDocumentService.get_component()

    async def upload_documents(
        self,
        documents: List[UploadFile],
        payload: UploadDocumentsRequestPayload,
    ) -> DocumentsData:
        created_by = payload.created_by or "Unknown"
        _logger.info(
            "Uploading %s documents to bucket: %s",
            len(documents),
            payload.bucket,
        )
        return await self.document_service.upload_documents(
            documents=documents,
            bucket=payload.bucket,
            created_by=created_by,
        )

    async def get_documents(self, request: GetDocumentsRequest) -> DocumentsData:
        payload = request.request_body.request_payload
        return await self.document_service.get_documents(payload.document_ids)

    async def delete_documents(self, request: DeleteDocumentsRequest) -> DeleteDocumentsData:
        payload = request.request_body.request_payload
        _logger.info(f"Deleting documents: {payload.document_ids}")
        return await self.document_service.delete_documents(payload.document_ids)

    async def get_change_request_documents(
        self,
        request: GetChangeRequestDocumentsRequest
    ) -> ChangeRequestDocumentsData:
        payload = request.request_body.request_payload
        return await self.document_service.get_change_request_documents(
            payload.change_request_id
        )

    async def get_intake_form_documents(
        self,
        request: GetIntakeFormDocumentsRequest
    ) -> IntakeFormDocumentsData:
        payload = request.request_body.request_payload
        return await self.document_service.get_intake_form_documents(
            payload.submission_id
        )

    async def get_section_documents(
        self,
        request: GetSectionDocumentsRequest
    ) -> SectionDocumentsData:
        payload = request.request_body.request_payload
        return await self.document_service.get_section_documents(
            payload.internal_record_id
        )
