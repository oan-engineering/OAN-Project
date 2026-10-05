from typing import Optional, List
from openg2p_fastapi_common.schemas import (
    G2PResponse,
    G2PResponseBody,
)
from .outgest_payload import (
    OutgestionSummaryData,
    OutgestionDataSearchResultData,
    OutgoingTopicData,
    OutgoingTemplateData,
)


# =============================================================================
# Outgestion Summary Response
# =============================================================================

class OutgestionSummaryDataResponseBody(G2PResponseBody):
    response_payload: Optional[OutgestionSummaryData] = None


class OutgestionSummaryDataResponse(G2PResponse):
    response_body: Optional[OutgestionSummaryDataResponseBody] = None


# =============================================================================
# Outgestion Search Response
# =============================================================================

class OutgestionDataSearchResultsResponseBody(G2PResponseBody):
    response_payload: Optional[List[OutgestionDataSearchResultData]] = None


class OutgestionDataSearchResultsResponse(G2PResponse):
    response_body: Optional[OutgestionDataSearchResultsResponseBody] = None


# =============================================================================
# OutgoingTopic Response Schemas
# =============================================================================

class OutgoingTopicResponseBody(G2PResponseBody):
    response_payload: Optional[OutgoingTopicData] = None


class OutgoingTopicResponse(G2PResponse):
    response_body: Optional[OutgoingTopicResponseBody] = None


class OutgoingTopicsResponseBody(G2PResponseBody):
    response_payload: Optional[List[OutgoingTopicData]] = None


class OutgoingTopicsResponse(G2PResponse):
    response_body: Optional[OutgoingTopicsResponseBody] = None


# =============================================================================
# OutgoingTemplate Response Schemas
# =============================================================================

class OutgoingTemplateResponseBody(G2PResponseBody):
    response_payload: Optional[OutgoingTemplateData] = None


class OutgoingTemplateResponse(G2PResponse):
    response_body: Optional[OutgoingTemplateResponseBody] = None


class OutgoingTemplatesResponseBody(G2PResponseBody):
    response_payload: Optional[List[OutgoingTemplateData]] = None


class OutgoingTemplatesResponse(G2PResponse):
    response_body: Optional[OutgoingTemplatesResponseBody] = None
