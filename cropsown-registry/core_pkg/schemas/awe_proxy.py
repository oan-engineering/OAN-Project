from typing import Any, List, Optional, TypeVar

from openg2p_fastapi_common.schemas import G2PRequest, G2PRequestBody, G2PResponse, G2PResponseBody
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R", bound=BaseModel)

# ``pagination_request`` field → resolved AWE/service payload field
_PAGINATION_FIELD_MAP = {
    "current_page": "page",
    "page_size": "page_size",
    "search_text": "search_text",
}


def merge_body_and_payload(
    body: G2PRequestBody,
    request_payload_cls: type[T],
    resolved_cls: type[R],
) -> R:
    """Build the effective payload from ``request_body``.

    ``request_payload_cls`` defines fields accepted in ``request_payload`` (Swagger).
    ``resolved_cls`` is the merged model passed to services; pagination fields are
    taken from ``pagination_request`` only.
    """
    request_field_names = set(request_payload_cls.model_fields)
    resolved_field_names = set(resolved_cls.model_fields)
    excluded = {"request_payload", "pagination_request"}

    body_data: dict[str, Any] = {
        key: value
        for key, value in body.model_dump(exclude=excluded, exclude_none=True).items()
        if key in request_field_names
    }

    payload_data: dict[str, Any] = {}
    if body.request_payload is not None:
        raw = body.request_payload
        payload_data = (
            raw.model_dump(exclude_none=True)
            if isinstance(raw, BaseModel)
            else dict(raw)
        )

    merged: dict[str, Any] = {
        **{key: value for key, value in body_data.items() if key not in payload_data},
        **payload_data,
    }

    if body.pagination_request:
        pagination = body.pagination_request.model_dump(exclude_none=True)
        for pag_key, resolved_key in _PAGINATION_FIELD_MAP.items():
            if resolved_key in resolved_field_names and pagination.get(pag_key) is not None:
                merged[resolved_key] = pagination[pag_key]

    return resolved_cls.model_validate(merged)


class AweProxyRequestBody(G2PRequestBody):
    """G2P request body that accepts duplicate AWE fields at the body root."""

    model_config = ConfigDict(extra="allow")

    def resolve_payload(
        self,
        request_payload_cls: type[T],
        resolved_cls: type[R] | None = None,
    ) -> T | R:
        target = resolved_cls or request_payload_cls
        return merge_body_and_payload(self, request_payload_cls, target)


class ListTasksForRequestRequestPayload(BaseModel):
    request_id: str


class ListTasksForRequestPayload(BaseModel):
    request_id: str
    page_size: int = Field(default=100, ge=1, le=100)


class ListMyAweTasksRequestPayload(BaseModel):
    """List tasks for the current user (assignee=me).

    Omit ``status`` to return tasks in every status (open, claimed, completed, …).
    Pass ``status='open'`` to return only open tasks.
    """

    request_id: Optional[str] = None
    status: Optional[str] = Field(
        default=None,
        description="Filter by task status (open, claimed, completed, …). Omit for all.",
    )
    artifact_type: Optional[str] = None
    policy_key: Optional[str] = None


class ListMyAweTasksPayload(BaseModel):
    request_id: Optional[str] = None
    status: Optional[str] = None
    artifact_type: Optional[str] = None
    policy_key: Optional[str] = None
    search_text: Optional[str] = None
    page: int = 1
    page_size: int = 25


class MyAweTaskStatsRequestPayload(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="Filter by task status. Omit to count tasks in every status.",
    )


class SubmitAweTaskDecisionRequestPayload(BaseModel):
    task_id: str
    action: str = Field(description="approve, reject, or abstain")
    comment: Optional[str] = None
    attachments_ref: Optional[str] = None
    artifact_id: str = Field(
        description="Registry artifact id (change_request_id or submission_id)",
    )
    artifact_type: str = Field(
        description="AWE artifact type, e.g. registry.change_request",
    )
    current_stage: int = Field(
        ge=1,
        description="Stage order the client saw when loading the approval UI",
    )


class ClaimAweTaskRequestPayload(BaseModel):
    task_id: str


class GetAweRequestRequestPayload(BaseModel):
    request_id: str


class GetAweRequestEventsRequestPayload(BaseModel):
    request_id: str


class AweProxyDataResponsePayload(BaseModel):
    data: Any


class ListTasksForRequestRequestBody(AweProxyRequestBody):
    request_payload: Optional[ListTasksForRequestRequestPayload] = None


class ListTasksForRequestRequest(G2PRequest):
    request_body: ListTasksForRequestRequestBody


class ListMyAweTasksRequestBody(AweProxyRequestBody):
    request_payload: Optional[ListMyAweTasksRequestPayload] = None


class ListMyAweTasksRequest(G2PRequest):
    request_body: ListMyAweTasksRequestBody


class MyAweTaskStatsRequestBody(AweProxyRequestBody):
    request_payload: Optional[MyAweTaskStatsRequestPayload] = None


class MyAweTaskStatsRequest(G2PRequest):
    request_body: MyAweTaskStatsRequestBody


class SubmitAweTaskDecisionRequestBody(AweProxyRequestBody):
    request_payload: Optional[SubmitAweTaskDecisionRequestPayload] = None


class SubmitAweTaskDecisionRequest(G2PRequest):
    request_body: SubmitAweTaskDecisionRequestBody


class ClaimAweTaskRequestBody(AweProxyRequestBody):
    request_payload: Optional[ClaimAweTaskRequestPayload] = None


class ClaimAweTaskRequest(G2PRequest):
    request_body: ClaimAweTaskRequestBody


class GetAweRequestRequestBody(AweProxyRequestBody):
    request_payload: Optional[GetAweRequestRequestPayload] = None


class GetAweRequestRequest(G2PRequest):
    request_body: GetAweRequestRequestBody


class GetAweRequestEventsRequestBody(AweProxyRequestBody):
    request_payload: Optional[GetAweRequestEventsRequestPayload] = None


class GetAweRequestEventsRequest(G2PRequest):
    request_body: GetAweRequestEventsRequestBody


class AweProxyDataResponseBody(G2PResponseBody):
    response_payload: Optional[AweProxyDataResponsePayload] = None


class AweProxyDataResponse(G2PResponse):
    response_body: Optional[AweProxyDataResponseBody] = None


class AweProxyListDataResponseBody(G2PResponseBody):
    response_payload: Optional[List[Any]] = None


class AweProxyListDataResponse(G2PResponse):
    response_body: Optional[AweProxyListDataResponseBody] = None
