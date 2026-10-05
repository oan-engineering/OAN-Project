from enum import Enum
from typing import Any, List, Optional

from openg2p_fastapi_common.schemas import G2PRequest, G2PRequestBody, G2PResponse, G2PResponseBody
from pydantic import BaseModel, ConfigDict

from ..models import ApprovalStatusEnum
from .file_payload import DocumentAttachment, DocumentData


# =============================================================================
# Table Data Schemas
# =============================================================================

class RegisterChangeRequestData(BaseModel):
    change_request_id: str
    record_name: Optional[str] = None
    register_id: str
    tab_id: str
    internal_record_id: str
    section_id: str
    section_register_id: str
    source_partner_id: str
    change_request_source: Optional[str] = None
    created_by: str
    created_at: Optional[str] = None
    no_of_verifications_required: Optional[int] = None
    no_of_verifications_done: Optional[int] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RegisterChangeRequestPayloadData(BaseModel):
    change_request_id: str
    change_payload: Optional[dict | List[dict]] = None
    search_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RegisterChangeRequestDocumentData(BaseModel):
    change_request_id: str
    section_id: str
    document_id: str
    label: str

    model_config = ConfigDict(from_attributes=True)


class RegisterVerificationData(BaseModel):
    verification_id: str
    register_id: str
    internal_record_id: Optional[str] = None
    section_id: Optional[str] = None
    change_request_id: Optional[str] = None
    verified_by: str
    verified_at: Optional[str] = None
    verification_observations: Optional[str] = None
    is_approved: bool

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Common Change Request Data Schemas
# =============================================================================

class ChangeRequestSummaryData(BaseModel):
    total_count: int
    approved_count: int
    pending_count: int


class ChangeRequestSearchResultData(BaseModel):
    change_request_id: str
    record_name: Optional[str] = None
    register_id: str
    register_mnemonic: str
    tab_id: str
    tab_label: str
    internal_record_id: str
    section_id: str
    section_mnemonic: str
    source_partner_id: str
    created_by: str
    created_at: Optional[str] = None
    no_of_verifications_required: Optional[int] = None
    no_of_verifications_done: Optional[int] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    change_payload: Optional[dict | List[dict]] = None

    model_config = ConfigDict(from_attributes=True)


class ChangeActionEnum(str, Enum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    NO_CHANGE = "NO_CHANGE"


class ChangePayload(BaseModel):
    internal_record_id: Optional[str] = None
    edit_action: str = ChangeActionEnum.ADD.value

    model_config = ConfigDict(extra="allow", from_attributes=True)


class ChangeRequestRequestPayload(BaseModel):
    register_id: Optional[str] = None
    register_mnemonic: Optional[str] = None
    tab_id: Optional[str] = None
    section_id: Optional[str] = None
    section_register_id: Optional[str] = None
    internal_record_id: Optional[str] = None
    change_payload: Optional[List[ChangePayload]] = None
    # Already-uploaded catalog documents with display labels
    documents: Optional[List[DocumentAttachment]] = None
    change_request_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None


class ChangeRequestResponsePayload(BaseModel):
    record_name: Optional[str] = None
    register_id: Optional[str] = None
    tab_id: Optional[str] = None
    section_id: Optional[str] = None
    section_register_id: Optional[str] = None
    no_of_verifications_required: Optional[int] = 0
    no_of_verifications_done: Optional[int] = 0
    approval_status: ApprovalStatusEnum = ApprovalStatusEnum.PENDING
    change_request_id: Optional[str] = None
    internal_record_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    awe_request_id: Optional[str] = None
    awe_request_status_summary: Optional[str] = None


class NumberOfPendingChangeRequestsData(BaseModel):
    subject_register_id: str
    subject_record_id: str
    tab_id: str
    number_of_pending_change_requests: int


class ChangeRequestSequenceCheckData(BaseModel):
    change_request_id: str
    internal_record_id: str
    has_earlier_pending_change_requests: bool
    number_of_earlier_pending_change_requests: int
    approval_decision_blocked: bool


class NumberOfCrossRegisterChangesData(BaseModel):
    subject_register_id: str
    subject_record_id: str
    number_of_cross_register_changes: int


class CrossRegisterChangeRequestData(BaseModel):
    change_request_id: str
    record_name: Optional[str] = None
    register_id: str
    register_mnemonic: str
    tab_id: str
    tab_label: str
    internal_record_id: str
    section_id: str
    source_partner_id: str
    created_by: str
    created_at: Optional[str] = None
    no_of_verifications_required: Optional[int] = None
    no_of_verifications_done: Optional[int] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CrossRegisterChangesData(BaseModel):
    cross_register_changes: list[CrossRegisterChangeRequestData]


class ChangeRequestData(BaseModel):
    change_request_id: str
    record_name: Optional[str] = None
    register_id: str
    tab_id: str
    internal_record_id: str
    section_id: str
    section_mnemonic: str
    is_list: bool = False
    section_register_id: str
    source_partner_id: str
    created_by: str
    created_at: Optional[str] = None
    no_of_verifications_required: Optional[int] = None
    no_of_verifications_done: Optional[int] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    awe_request_id: Optional[str] = None
    awe_request_status_summary: Optional[str] = None
    change_payload: Optional[dict | List[dict]] = None
    current_register_data: Optional[dict | List[dict]] = None
    documents: Optional[List[DocumentData]] = None

    model_config = ConfigDict(from_attributes=True)


class ChangeRequestFlattenedData(BaseModel):
    change_request_id: str
    record_name: Optional[str] = None
    register_id: str
    tab_id: str
    internal_record_id: str
    section_id: str
    section_mnemonic: str
    source_partner_id: str
    created_by: str
    created_at: Optional[str] = None
    no_of_verifications_required: Optional[int] = None
    no_of_verifications_done: Optional[int] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

    model_config = ConfigDict(extra="allow", from_attributes=True)


class ChangeRequestsData(BaseModel):
    change_requests: List[ChangeRequestData]

    model_config = ConfigDict(from_attributes=True)


class VerificationData(RegisterVerificationData):
    pass


class VerificationsData(BaseModel):
    verifications: List[VerificationData]

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Endpoint Request Payload Schemas
# =============================================================================

class ChangeRequestEmptyRequestPayload(BaseModel):
    pass


class SearchChangeRequestRequestPayload(BaseModel):
    pass


class GetNumberOfPendingChangeRequestsRequestPayload(BaseModel):
    subject_register_id: str
    subject_record_id: str
    tab_id: str


class GetNumberOfCrossRegisterChangesRequestPayload(BaseModel):
    subject_register_id: str
    subject_record_id: str


class GetCrossRegisterChangesRequestPayload(BaseModel):
    subject_register_id: str
    subject_record_id: str


class GetChangeRequestsRequestPayload(BaseModel):
    subject_register_id: str
    subject_record_id: str
    tab_id: str


class GetChangeRequestRequestPayload(BaseModel):
    change_request_id: str


class CheckChangeRequestSequenceRequestPayload(BaseModel):
    change_request_id: str


class GetVerificationsRequestPayload(BaseModel):
    change_request_id: Optional[str] = None
    submission_id: Optional[str] = None


class AddVerificationPayload(BaseModel):
    submission_id: Optional[str] = None
    change_request_id: Optional[str] = None
    verification_observations: Optional[str] = None
    verified_by: Optional[str] = None
    is_approved: bool


# =============================================================================
# Request Schemas
# =============================================================================

class ChangeRequestRequestBody(G2PRequestBody):
    request_payload: ChangeRequestRequestPayload


class ChangeRequestRequest(G2PRequest):
    request_body: ChangeRequestRequestBody


class GetChangeRequestSummaryDataRequestBody(G2PRequestBody):
    request_payload: ChangeRequestEmptyRequestPayload


class GetChangeRequestSummaryDataRequest(G2PRequest):
    request_body: GetChangeRequestSummaryDataRequestBody


class SearchChangeRequestRequestBody(G2PRequestBody):
    request_payload: SearchChangeRequestRequestPayload


class SearchChangeRequestRequest(G2PRequest):
    request_body: SearchChangeRequestRequestBody


class GetNumberOfPendingChangeRequestsRequestBody(G2PRequestBody):
    request_payload: GetNumberOfPendingChangeRequestsRequestPayload


class GetNumberOfPendingChangeRequestsRequest(G2PRequest):
    request_body: GetNumberOfPendingChangeRequestsRequestBody


class GetNumberOfCrossRegisterChangesRequestBody(G2PRequestBody):
    request_payload: GetNumberOfCrossRegisterChangesRequestPayload


class GetNumberOfCrossRegisterChangesRequest(G2PRequest):
    request_body: GetNumberOfCrossRegisterChangesRequestBody


class GetCrossRegisterChangesRequestBody(G2PRequestBody):
    request_payload: GetCrossRegisterChangesRequestPayload


class GetCrossRegisterChangesRequest(G2PRequest):
    request_body: GetCrossRegisterChangesRequestBody


class GetChangeRequestsRequestBody(G2PRequestBody):
    request_payload: GetChangeRequestsRequestPayload


class GetChangeRequestsRequest(G2PRequest):
    request_body: GetChangeRequestsRequestBody


class GetChangeRequestRequestBody(G2PRequestBody):
    request_payload: GetChangeRequestRequestPayload


class GetChangeRequestRequest(G2PRequest):
    request_body: GetChangeRequestRequestBody


class CheckChangeRequestSequenceRequestBody(G2PRequestBody):
    request_payload: CheckChangeRequestSequenceRequestPayload


class CheckChangeRequestSequenceRequest(G2PRequest):
    request_body: CheckChangeRequestSequenceRequestBody


class GetVerificationsRequestBody(G2PRequestBody):
    request_payload: GetVerificationsRequestPayload


class GetVerificationsRequest(G2PRequest):
    request_body: GetVerificationsRequestBody


class AddVerificationRequestBody(G2PRequestBody):
    request_payload: AddVerificationPayload


class AddVerificationRequest(G2PRequest):
    request_body: AddVerificationRequestBody


# =============================================================================
# Response Schemas
# =============================================================================

class ChangeRequestResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestResponsePayload] = None


class ChangeRequestResponse(G2PResponse):
    response_body: Optional[ChangeRequestResponseBody] = None


class ChangeRequestSummaryDataResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestSummaryData] = None


class ChangeRequestSummaryDataResponse(G2PResponse):
    response_body: Optional[ChangeRequestSummaryDataResponseBody] = None


class ChangeRequestSearchResultsResponseBody(G2PResponseBody):
    response_payload: Optional[List[ChangeRequestSearchResultData]] = None


class ChangeRequestSearchResultsResponse(G2PResponse):
    response_body: Optional[ChangeRequestSearchResultsResponseBody] = None


class NumberOfPendingChangeRequestsResponseBody(G2PResponseBody):
    response_payload: Optional[NumberOfPendingChangeRequestsData] = None


class NumberOfPendingChangeRequestsResponse(G2PResponse):
    response_body: Optional[NumberOfPendingChangeRequestsResponseBody] = None


class ChangeRequestSequenceCheckResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestSequenceCheckData] = None


class ChangeRequestSequenceCheckResponse(G2PResponse):
    response_body: Optional[ChangeRequestSequenceCheckResponseBody] = None


class NumberOfCrossRegisterChangesResponseBody(G2PResponseBody):
    response_payload: Optional[NumberOfCrossRegisterChangesData] = None


class NumberOfCrossRegisterChangesResponse(G2PResponse):
    response_body: Optional[NumberOfCrossRegisterChangesResponseBody] = None


class CrossRegisterChangesDataResponseBody(G2PResponseBody):
    response_payload: Optional[CrossRegisterChangesData] = None


class CrossRegisterChangesDataResponse(G2PResponse):
    response_body: Optional[CrossRegisterChangesDataResponseBody] = None


class ChangeRequestDataResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestData] = None


class ChangeRequestDataResponse(G2PResponse):
    response_body: Optional[ChangeRequestDataResponseBody] = None


class ChangeRequestsDataResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestsData] = None


class ChangeRequestsDataResponse(G2PResponse):
    response_body: Optional[ChangeRequestsDataResponseBody] = None


class ChangeRequestFlattenedDataResponseBody(G2PResponseBody):
    response_payload: Optional[List[ChangeRequestFlattenedData]] = None


class ChangeRequestFlattenedDataResponse(G2PResponse):
    response_body: Optional[ChangeRequestFlattenedDataResponseBody] = None


class VerificationsDataResponseBody(G2PResponseBody):
    response_payload: Optional[VerificationsData] = None


class VerificationsDataResponse(G2PResponse):
    response_body: Optional[VerificationsDataResponseBody] = None


class VerificationDataResponseBody(G2PResponseBody):
    response_payload: Optional[VerificationData] = None


class VerificationDataResponse(G2PResponse):
    response_body: Optional[VerificationDataResponseBody] = None
