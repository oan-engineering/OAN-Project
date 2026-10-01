from typing import Optional, List
from openg2p_fastapi_common.schemas import (
    G2PResponse,
    G2PResponseBody,
)
from .ingest_payload import (
    IngestionSummaryData,
    IngestionDataSearchResultData,
    IngestionDataPayload,
    IngestDataPayload,
    IncomingPartnerData,
    IncomingModelKeyPathData,
    IncomingModelKeyPathListData,
    IncomingModelSemanticPatternData,
    IncomingModelRegisterSemanticPatternData,
    IncomingTemplateData,
    DataModelData,
    SubscriptionActivityLogData,
    G2PInputMechanismData
)


# =============================================================================
# Ingest Data Response
# =============================================================================

class IngestDataResponseBody(G2PResponseBody):
    response_payload: Optional[IngestDataPayload] = None


class IngestDataResponse(G2PResponse):
    response_body: Optional[IngestDataResponseBody] = None


# =============================================================================
# Ingestion Summary Response
# =============================================================================

class IngestionSummaryDataResponseBody(G2PResponseBody):
    response_body: Optional[IngestionSummaryData] = None


class IngestionSummaryDataResponse(G2PResponse):
    response_body: Optional[IngestionSummaryDataResponseBody] = None


# =============================================================================
# Ingestion Search Response
# =============================================================================

class IngestionDataSearchResultsResponseBody(G2PResponseBody):
    response_payload: Optional[List[IngestionDataSearchResultData]] = None


class IngestionDataSearchResultsResponse(G2PResponse):
    response_body: Optional[IngestionDataSearchResultsResponseBody] = None


# =============================================================================
# Ingestion Data Payload Response
# =============================================================================

class IngestionDataPayloadResponseBody(G2PResponseBody):
    response_payload: Optional[IngestionDataPayload] = None


class IngestionDataPayloadResponse(G2PResponse):
    response_body: Optional[IngestionDataPayloadResponseBody] = None


# =============================================================================
# IncomingPartner Response Schemas
# =============================================================================

class IncomingPartnerResponseBody(G2PResponseBody):
    response_payload: Optional[IncomingPartnerData] = None


class IncomingPartnerResponse(G2PResponse):
    response_body: Optional[IncomingPartnerResponseBody] = None


class IncomingPartnersResponseBody(G2PResponseBody):
    response_payload: Optional[List[IncomingPartnerData]] = None


class IncomingPartnersResponse(G2PResponse):
    response_body: Optional[IncomingPartnersResponseBody] = None


# =============================================================================
# IncomingModelKeyPath Response Schemas
# =============================================================================

class IncomingModelKeyPathResponseBody(G2PResponseBody):
    response_payload: Optional[IncomingModelKeyPathData] = None


class IncomingModelKeyPathResponse(G2PResponse):
    response_body: Optional[IncomingModelKeyPathResponseBody] = None


class IncomingModelKeyPathsResponseBody(G2PResponseBody):
    response_payload: Optional[List[IncomingModelKeyPathData]] = None


class IncomingModelKeyPathsResponse(G2PResponse):
    response_body: Optional[IncomingModelKeyPathsResponseBody] = None


# List response for IncomingModelKeyPath with data_model_mnemonic
class IncomingModelKeyPathListResponseBody(G2PResponseBody):
    response_payload: Optional[List[IncomingModelKeyPathListData]] = None


class IncomingModelKeyPathListResponse(G2PResponse):
    response_body: Optional[IncomingModelKeyPathListResponseBody] = None


# =============================================================================
# IncomingModelSemanticPattern Response Schemas
# =============================================================================

class IncomingModelSemanticPatternResponseBody(G2PResponseBody):
    response_payload: Optional[IncomingModelSemanticPatternData] = None


class IncomingModelSemanticPatternResponse(G2PResponse):
    response_body: Optional[IncomingModelSemanticPatternResponseBody] = None


class IncomingModelSemanticPatternsResponseBody(G2PResponseBody):
    response_payload: Optional[List[IncomingModelSemanticPatternData]] = None


class IncomingModelSemanticPatternsResponse(G2PResponse):
    response_body: Optional[IncomingModelSemanticPatternsResponseBody] = None


# =============================================================================
# IncomingModelRegisterSemanticPattern Response Schemas
# =============================================================================


class IncomingModelRegisterSemanticPatternResponseBody(G2PResponseBody):
    response_payload: Optional[IncomingModelRegisterSemanticPatternData] = None


class IncomingModelRegisterSemanticPatternResponse(G2PResponse):
    response_body: Optional[IncomingModelRegisterSemanticPatternResponseBody] = None


class IncomingModelRegisterSemanticPatternsResponseBody(G2PResponseBody):
    response_payload: Optional[List[IncomingModelRegisterSemanticPatternData]] = None


class IncomingModelRegisterSemanticPatternsResponse(G2PResponse):
    response_body: Optional[IncomingModelRegisterSemanticPatternsResponseBody] = None


# =============================================================================
# IncomingTemplate Response Schemas
# =============================================================================

class IncomingTemplateResponseBody(G2PResponseBody):
    response_payload: Optional[IncomingTemplateData] = None


class IncomingTemplateResponse(G2PResponse):
    response_body: Optional[IncomingTemplateResponseBody] = None


class IncomingTemplatesResponseBody(G2PResponseBody):
    response_payload: Optional[List[IncomingTemplateData]] = None


class IncomingTemplatesResponse(G2PResponse):
    response_body: Optional[IncomingTemplatesResponseBody] = None


# =============================================================================
# DataModel Response Schemas
# =============================================================================

class DataModelResponseBody(G2PResponseBody):
    response_payload: Optional[DataModelData] = None


class DataModelResponse(G2PResponse):
    response_body: Optional[DataModelResponseBody] = None


class DataModelsResponseBody(G2PResponseBody):
    response_payload: Optional[List[DataModelData]] = None


class DataModelsResponse(G2PResponse):
    response_body: Optional[DataModelsResponseBody] = None


# =============================================================================
# SubscriptionActivityLog Response Schemas
# =============================================================================

class SubscriptionActivityLogResponseBody(G2PResponseBody):
    response_payload: Optional[SubscriptionActivityLogData] = None


class SubscriptionActivityLogResponse(G2PResponse):
    response_body: Optional[SubscriptionActivityLogResponseBody] = None


class SubscriptionActivityLogsResponseBody(G2PResponseBody):
    response_payload: Optional[List[SubscriptionActivityLogData]] = None


class SubscriptionActivityLogsResponse(G2PResponse):
    response_body: Optional[SubscriptionActivityLogsResponseBody] = None


# =============================================================================
# G2P Input Mechanism Response Schemas
# =============================================================================

class G2PInputMechanismResponseBody(G2PResponseBody):
    response_payload: Optional[List[G2PInputMechanismData]] = None


class G2PInputMechanismResponse(G2PResponse):
    response_body: Optional[G2PInputMechanismResponseBody] = None
