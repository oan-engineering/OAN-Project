from datetime import datetime
from typing import Any

from openg2p_fastapi_common.schemas import (
    G2PRequest,
    G2PRequestBody,
    G2PResponse,
    G2PResponseBody,
)
from pydantic import BaseModel


class RegistrantAuthProviderSummary(BaseModel):
    provider_id: str
    provider_name: str
    provider_description: str | None = None
    adapter_name: str
    display_order: int = 0


class RegistrantAuthHistoryItem(BaseModel):
    authentication_id: str
    initiated_at: datetime
    status: str
    authentication_method: str | None = None
    initiated_by_staff_id: str
    claim_verifications: dict[str, Any] | None = None
    expiry_at: datetime | None = None
    failure_reason: str | None = None


class RegistrantAuthProvidersRequestPayload(BaseModel):
    register_id: str


class RegistrantAuthProvidersRequestBody(G2PRequestBody):
    request_payload: RegistrantAuthProvidersRequestPayload


class RegistrantAuthProvidersRequest(G2PRequest):
    request_body: RegistrantAuthProvidersRequestBody


class RegistrantAuthProvidersResponsePayload(BaseModel):
    providers: list[RegistrantAuthProviderSummary]


class RegistrantAuthProvidersResponseBody(G2PResponseBody):
    response_payload: RegistrantAuthProvidersResponsePayload | None = None


class RegistrantAuthProvidersResponse(G2PResponse):
    response_body: RegistrantAuthProvidersResponseBody


class RegistrantAuthInitiateRequestPayload(BaseModel):
    register_id: str
    internal_record_id: str
    provider_id: str
    initiated_by_staff_id: str


class RegistrantAuthInitiateRequestBody(G2PRequestBody):
    request_payload: RegistrantAuthInitiateRequestPayload


class RegistrantAuthInitiateRequest(G2PRequest):
    request_body: RegistrantAuthInitiateRequestBody


class RegistrantAuthInitiateResponsePayload(BaseModel):
    authentication_session_id: str
    authorization_url: str
    provider_name: str


class RegistrantAuthInitiateResponseBody(G2PResponseBody):
    response_payload: RegistrantAuthInitiateResponsePayload | None = None


class RegistrantAuthInitiateResponse(G2PResponse):
    response_body: RegistrantAuthInitiateResponseBody


class RegistrantAuthStatusRequestPayload(BaseModel):
    internal_record_id: str


class RegistrantAuthStatusRequestBody(G2PRequestBody):
    request_payload: RegistrantAuthStatusRequestPayload


class RegistrantAuthStatusRequest(G2PRequest):
    request_body: RegistrantAuthStatusRequestBody


class RegistrantAuthStatusResponsePayload(BaseModel):
    authentication: RegistrantAuthHistoryItem | None


class RegistrantAuthStatusResponseBody(G2PResponseBody):
    response_payload: RegistrantAuthStatusResponsePayload | None = None


class RegistrantAuthStatusResponse(G2PResponse):
    response_body: RegistrantAuthStatusResponseBody


class RegistrantAuthHistoryRequestPayload(BaseModel):
    internal_record_id: str


class RegistrantAuthHistoryRequestBody(G2PRequestBody):
    request_payload: RegistrantAuthHistoryRequestPayload


class RegistrantAuthHistoryRequest(G2PRequest):
    request_body: RegistrantAuthHistoryRequestBody


class RegistrantAuthHistoryResponsePayload(BaseModel):
    authentications: list[RegistrantAuthHistoryItem]


class RegistrantAuthHistoryResponseBody(G2PResponseBody):
    response_payload: RegistrantAuthHistoryResponsePayload | None = None


class RegistrantAuthHistoryResponse(G2PResponse):
    response_body: RegistrantAuthHistoryResponseBody


class RegistrantAuthCallbackCompleteRequest(BaseModel):
    code: str
    state: str

