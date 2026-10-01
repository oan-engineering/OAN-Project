
from typing import Dict, List, Optional

from openg2p_fastapi_common.schemas import G2PRequest, G2PRequestBody, G2PResponse, G2PResponseBody
from pydantic import BaseModel, ConfigDict

from .register_payload import DisplayField
from .file_payload import DocumentAttachment, DocumentData


class G2PIntakeFormSchemaBase:
    submission_id: Optional[str] = None
    application_reference: Optional[str] = None


class IntakeFormData(BaseModel):
    submission_id: Optional[str] = None
    application_reference: Optional[str] = None
    form_id: Optional[str] = None
    register_id: Optional[str] = None
    draft_status: Optional[str] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    finalized_at: Optional[str] = None
    first_created_at: Optional[str] = None
    submission_source: Optional[str] = None
    partner_id: Optional[str] = None
    register_ingest_process_status: Optional[str] = None
    register_ingest_processed_timestamp: Optional[str] = None
    register_ingest_process_attempts: Optional[int] = None
    register_ingest_process_last_error_code: Optional[str] = None
    number_of_verifications_required: Optional[int] = None
    number_of_verifications_done: Optional[int] = None
    created_by: Optional[str] = None
    last_updated_at: Optional[str] = None
    awe_request_id: Optional[str] = None
    awe_request_status_summary: Optional[str] = None

    deduplication_status_vs_intake_forms: Optional[str] = None
    deduplication_intake_forms_process_timestamp: Optional[str] = None
    deduplication_intake_forms_attempts: Optional[int] = None
    deduplication_intake_forms_error: Optional[str] = None

    deduplication_status_vs_register: Optional[str] = None
    deduplication_register_process_timestamp: Optional[str] = None
    deduplication_register_forms_attempts: Optional[int] = None
    deduplication_register_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SectionPayloadResponseItem(BaseModel):
    section_id: str
    section_register_id: str
    is_list: bool
    section_order: Optional[int] = None
    records: List[dict]
    documents: Optional[List[DocumentData]] = None


class SubmissionResponsePayload(IntakeFormData):
    record_name: Optional[str] = None
    section_payloads: Optional[List[SectionPayloadResponseItem]] = None
    display_fields: Optional[List[DisplayField]] = None


class SectionPayloadInput(BaseModel):
    section_id: str
    intake_form_section_payload: List[dict]
    # Desired document set for the section (g2p_registry_documents).
    # None = no-op; [] = clear; list = full desired set (diff-synced by document_id).
    documents: Optional[List[DocumentAttachment]] = None


class SaveIntakeFormSubmissionRequestPayload(BaseModel):
    submission_id: Optional[str] = None
    section_id: str
    section_payload: List[dict]
    section_register_id: str
    form_id: str
    register_id: str
    created_by: Optional[str] = None
    # Desired document set for the section (g2p_registry_documents).
    # None = no-op; [] = clear; list = full desired set (diff-synced by document_id).
    documents: Optional[List[DocumentAttachment]] = None


class SaveIntakeFormSubmissionRequestBody(G2PRequestBody):
    request_payload: SaveIntakeFormSubmissionRequestPayload


class SaveIntakeFormSubmissionRequest(G2PRequest):
    request_body: SaveIntakeFormSubmissionRequestBody


class SaveSubmissionDraftRequestPayload(BaseModel):
    submission_id: Optional[str] = None
    form_id: str
    register_id: str
    submission_source: Optional[str] = None
    partner_id: Optional[str] = None
    section_payloads: Optional[List[SectionPayloadInput]] = None
    created_by: Optional[str] = None


class DeleteIntakeFormSubmissionRequestPayload(BaseModel):
    submission_id: str


class FinalizeSubmissionRequestPayload(BaseModel):
    submission_id: str


class ApproveRejectSubmissionRequestPayload(BaseModel):
    submission_id: str
    approved_by: Optional[str] = None


class GetSubmissionRequestPayload(BaseModel):
    submission_id: str


class SearchInSubmissionRequestPayload(BaseModel):
    register_id: str


class GetIntakeFormTabRecordsRequestPayload(BaseModel):
    submission_id: str
    tab_id: str


class SaveSubmissionDraftRequestBody(G2PRequestBody):
    request_payload: SaveSubmissionDraftRequestPayload


class SaveSubmissionDraftRequest(G2PRequest):
    request_body: SaveSubmissionDraftRequestBody


class DeleteIntakeFormSubmissionRequestBody(G2PRequestBody):
    request_payload: DeleteIntakeFormSubmissionRequestPayload


class DeleteIntakeFormSubmissionRequest(G2PRequest):
    request_body: DeleteIntakeFormSubmissionRequestBody


class FinalizeSubmissionRequestBody(G2PRequestBody):
    request_payload: FinalizeSubmissionRequestPayload


class FinalizeSubmissionRequest(G2PRequest):
    request_body: FinalizeSubmissionRequestBody


class ApproveRejectSubmissionRequestBody(G2PRequestBody):
    request_payload: ApproveRejectSubmissionRequestPayload


class ApproveRejectSubmissionRequest(G2PRequest):
    request_body: ApproveRejectSubmissionRequestBody


class GetSubmissionRequestBody(G2PRequestBody):
    request_payload: GetSubmissionRequestPayload


class GetSubmissionRequest(G2PRequest):
    request_body: GetSubmissionRequestBody


class SearchInSubmissionRequestBody(G2PRequestBody):
    request_payload: SearchInSubmissionRequestPayload


class SearchInSubmissionRequest(G2PRequest):
    request_body: SearchInSubmissionRequestBody


class GetIntakeFormTabRecordsRequestBody(G2PRequestBody):
    request_payload: GetIntakeFormTabRecordsRequestPayload


class GetIntakeFormTabRecordsRequest(G2PRequest):
    request_body: GetIntakeFormTabRecordsRequestBody


class GetIntakeFormTabRecordsResponseBody(G2PResponseBody):
    response_payload: Optional[List[SectionPayloadResponseItem]] = None


class GetIntakeFormTabRecordsResponse(G2PResponse):
    response_body: Optional[GetIntakeFormTabRecordsResponseBody] = None


class SubmissionResponseBody(G2PResponseBody):
    response_payload: Optional[SubmissionResponsePayload] = None


class SubmissionResponse(G2PResponse):
    response_body: Optional[SubmissionResponseBody] = None


class SubmissionSearchResultsResponseBody(G2PResponseBody):
    response_payload: Optional[List[SubmissionResponsePayload]] = None


class SubmissionSearchResultsResponse(G2PResponse):
    response_body: Optional[SubmissionSearchResultsResponseBody] = None


# --- Intake Form Deduplication Schemas ---

class DeduplicationIntakeFormRegisterResultData(BaseModel):
    dedup_result_id: str
    submission_id: str
    section_register_id: str
    section_register_mnemonic: str
    internal_record_id: str
    match_score: float
    field_matches: Optional[Dict] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DeduplicationIntakeFormIntakeFormResultData(BaseModel):
    dedup_result_id: str
    submission_id: str
    section_register_id: str
    section_register_mnemonic: str
    candidate_submission_id: str
    match_score: float
    field_matches: Optional[Dict] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GetDeduplicationIntakeFormRegisterResultsRequestPayload(BaseModel):
    submission_id: str


class GetDeduplicationIntakeFormRegisterResultsRequestBody(G2PRequestBody):
    request_payload: GetDeduplicationIntakeFormRegisterResultsRequestPayload


class GetDeduplicationIntakeFormRegisterResultsRequest(G2PRequest):
    request_body: GetDeduplicationIntakeFormRegisterResultsRequestBody


class GetDeduplicationIntakeFormIntakeFormResultsRequestPayload(BaseModel):
    submission_id: str


class GetDeduplicationIntakeFormIntakeFormResultsRequestBody(G2PRequestBody):
    request_payload: GetDeduplicationIntakeFormIntakeFormResultsRequestPayload


class GetDeduplicationIntakeFormIntakeFormResultsRequest(G2PRequest):
    request_body: GetDeduplicationIntakeFormIntakeFormResultsRequestBody


class DeduplicationIntakeFormRegisterResultsResponseBody(G2PResponseBody):
    response_payload: Optional[List[DeduplicationIntakeFormRegisterResultData]] = None


class DeduplicationIntakeFormRegisterResultsResponse(G2PResponse):
    response_body: Optional[DeduplicationIntakeFormRegisterResultsResponseBody] = None


class DeduplicationIntakeFormIntakeFormResultsResponseBody(G2PResponseBody):
    response_payload: Optional[List[DeduplicationIntakeFormIntakeFormResultData]] = None


class DeduplicationIntakeFormIntakeFormResultsResponse(G2PResponse):
    response_body: Optional[DeduplicationIntakeFormIntakeFormResultsResponseBody] = None
