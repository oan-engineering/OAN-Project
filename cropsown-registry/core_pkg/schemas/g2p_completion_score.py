from typing import List, Optional
from pydantic import BaseModel
from openg2p_fastapi_common.schemas import (
    G2PRequest,
    G2PRequestBody,
    G2PResponse,
    G2PResponseBody,
)


class RegisterIdPayload(BaseModel):
    register_id: str


class SectionIdPayload(BaseModel):
    section_id: str


class RecordSectionPayload(BaseModel):
    register_id: str
    internal_record_id: str
    section_id: str


class RecordPayload(BaseModel):
    register_id: str
    internal_record_id: str


class IdealRegisterScoreData(BaseModel):
    register_id: str
    ideal_completion_score: float


class IdealSectionScoreData(BaseModel):
    section_id: str
    section_weightage: float


class SectionCompletionScoreData(BaseModel):
    register_id: str
    internal_record_id: str
    section_id: str
    computed_section_completion_score: float
    section_weightage: float
    computed_timestamp: Optional[str] = None


class RecordCompletionScoreData(BaseModel):
    register_id: str
    internal_record_id: str
    section_scores: List[SectionCompletionScoreData]
    actual_score: float
    ideal_score: float


# Requests
class GetIdealCompletionScoreForRegisterRequestBody(G2PRequestBody):
    request_payload: RegisterIdPayload


class GetIdealCompletionScoreForRegisterRequest(G2PRequest):
    request_body: GetIdealCompletionScoreForRegisterRequestBody


class GetIdealCompletionScoreForSectionRequestBody(G2PRequestBody):
    request_payload: SectionIdPayload


class GetIdealCompletionScoreForSectionRequest(G2PRequest):
    request_body: GetIdealCompletionScoreForSectionRequestBody


class GetComputedCompletionScoreForSectionRequestBody(G2PRequestBody):
    request_payload: RecordSectionPayload


class GetComputedCompletionScoreForSectionRequest(G2PRequest):
    request_body: GetComputedCompletionScoreForSectionRequestBody


class GetComputedCompletionScoreForRecordRequestBody(G2PRequestBody):
    request_payload: RecordPayload


class GetComputedCompletionScoreForRecordRequest(G2PRequest):
    request_body: GetComputedCompletionScoreForRecordRequestBody


# Responses
class IdealRegisterScoreResponseBody(G2PResponseBody):
    response_payload: IdealRegisterScoreData


class IdealRegisterScoreResponse(G2PResponse):
    response_body: IdealRegisterScoreResponseBody


class IdealSectionScoreResponseBody(G2PResponseBody):
    response_payload: IdealSectionScoreData


class IdealSectionScoreResponse(G2PResponse):
    response_body: IdealSectionScoreResponseBody


class SectionCompletionScoreResponseBody(G2PResponseBody):
    response_payload: SectionCompletionScoreData


class SectionCompletionScoreResponse(G2PResponse):
    response_body: SectionCompletionScoreResponseBody


class RecordCompletionScoreResponseBody(G2PResponseBody):
    response_payload: RecordCompletionScoreData


class RecordCompletionScoreResponse(G2PResponse):
    response_body: RecordCompletionScoreResponseBody
