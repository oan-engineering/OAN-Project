from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from ..models.enum import DocumentBucket


class DocumentAttachment(BaseModel):
    """Reference to an already-uploaded catalog document with a required display label."""

    document_id: str
    label: str


class DocumentData(BaseModel):
    """g2p_registry_documents model attributes + presigned URL."""

    document_id: str
    document_store_id: str
    bucket: DocumentBucket
    source_filename: str
    created_by: str
    created_at: datetime
    presigned_url: Optional[str] = None
    # Populated by the per-entity document queries (CR / intake / section)
    section_id: Optional[str] = None
    # From junction tables on entity GETs; absent on plain upload / get_documents
    label: Optional[str] = None

    class Config:
        from_attributes: bool = True


class DocumentsData(BaseModel):
    documents: List[DocumentData]


class ChangeRequestDocumentsData(DocumentsData):
    change_request_id: str


class IntakeFormDocumentsData(DocumentsData):
    submission_id: str


class SectionDocumentsData(DocumentsData):
    internal_record_id: str


class DeleteDocumentsData(BaseModel):
    deleted_document_ids: List[str]


class UploadDocumentsRequestPayload(BaseModel):
    bucket: DocumentBucket = DocumentBucket.DOCUMENTS
    created_by: Optional[str] = None


class UploadTemplateRequestPayload(BaseModel):
    created_by: Optional[str] = None


class GetDocumentsRequestPayload(BaseModel):
    document_ids: List[str]


class DeleteDocumentsRequestPayload(BaseModel):
    document_ids: List[str]


class GetChangeRequestDocumentsRequestPayload(BaseModel):
    change_request_id: str


class GetIntakeFormDocumentsRequestPayload(BaseModel):
    submission_id: str


class GetSectionDocumentsRequestPayload(BaseModel):
    internal_record_id: str
