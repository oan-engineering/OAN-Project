from openg2p_fastapi_common.schemas import (
    G2PRequest,
    G2PRequestBody,
)
from .outgest_payload import (
    EmptyOutgestionRequestPayload,
    GetOutgoingTopicPayload,
    GetOutgoingTemplatePayload,
    OutgoingTopicPayload,
    OutgoingTopicUpdatePayload,
    OutgoingTemplatePayload,
    OutgoingTemplateUpdatePayload,
)


# =============================================================================
# OutgoingTopic Request Schemas
# =============================================================================

class OutgoingTopicRequestBody(G2PRequestBody):
    request_payload: OutgoingTopicPayload


class OutgoingTopicRequest(G2PRequest):
    request_body: OutgoingTopicRequestBody


class OutgoingTopicIdRequestBody(G2PRequestBody):
    request_payload: GetOutgoingTopicPayload


class OutgoingTopicIdRequest(G2PRequest):
    request_body: OutgoingTopicIdRequestBody


class OutgoingTopicUpdateRequestBody(G2PRequestBody):
    request_payload: OutgoingTopicUpdatePayload


class OutgoingTopicUpdateRequest(G2PRequest):
    request_body: OutgoingTopicUpdateRequestBody


class GetAllOutgoingTopicsRequestBody(G2PRequestBody):
    request_payload: EmptyOutgestionRequestPayload


class GetAllOutgoingTopicsRequest(G2PRequest):
    request_body: GetAllOutgoingTopicsRequestBody


# =============================================================================
# OutgoingTemplate Request Schemas
# =============================================================================

class OutgoingTemplateRequestBody(G2PRequestBody):
    request_payload: OutgoingTemplatePayload


class OutgoingTemplateRequest(G2PRequest):
    request_body: OutgoingTemplateRequestBody


class OutgoingTemplateIdRequestBody(G2PRequestBody):
    request_payload: GetOutgoingTemplatePayload


class OutgoingTemplateIdRequest(G2PRequest):
    request_body: OutgoingTemplateIdRequestBody


class OutgoingTemplateUpdateRequestBody(G2PRequestBody):
    request_payload: OutgoingTemplateUpdatePayload


class OutgoingTemplateUpdateRequest(G2PRequest):
    request_body: OutgoingTemplateUpdateRequestBody


class GetAllOutgoingTemplatesRequestBody(G2PRequestBody):
    request_payload: EmptyOutgestionRequestPayload


class GetAllOutgoingTemplatesRequest(G2PRequest):
    request_body: GetAllOutgoingTemplatesRequestBody


# =============================================================================
# Outgestion Data Requests
# =============================================================================

class GetOutgestionSummaryDataRequestBody(G2PRequestBody):
    request_payload: EmptyOutgestionRequestPayload


class GetOutgestionSummaryDataRequest(G2PRequest):
    request_body: GetOutgestionSummaryDataRequestBody


class SearchOutgestionDataRequestBody(G2PRequestBody):
    request_payload: EmptyOutgestionRequestPayload


class SearchOutgestionDataRequest(G2PRequest):
    request_body: SearchOutgestionDataRequestBody
