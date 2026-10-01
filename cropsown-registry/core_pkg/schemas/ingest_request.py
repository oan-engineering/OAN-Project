from fastapi import Request
from openg2p_fastapi_common.schemas import (
    G2PRequest,
    G2PRequestBody,
)
from .ingest_payload import (
    EmptyIngestionRequestPayload,
    GetIngestionDataRequestPayload,
    IncomingPartnerPayload,
    IncomingPartnerUpdatePayload,
    GetIncomingKeyPathPayload,
    IncomingModelKeyPathPayload,
    IncomingModelKeyPathUpdatePayload,
    IncomingModelSemanticPatternPayload,
    GetIncomingSemanticPatternPayload,
    IncomingModelSemanticPatternUpdatePayload,
    IncomingModelRegisterSemanticPatternPayload,
    GetIncomingRegisterSemanticPatternPayload,
    IncomingModelRegisterSemanticPatternUpdatePayload,
    IncomingTemplatePayload,
    GetIncomingTemplatePayload,
    IncomingTemplateUpdatePayload,
    DataModelPayload,
    DataModelIdPayload,
    DataModelUpdatePayload,
    ChangeResponseTemplateFilePayload,
    ChangeActiveStatusPayload,
    SubscriptionActivityLogPayload,
    G2PInputMechanismPayload
)


# =============================================================================
# Ingest Data Request (base request for ingestion)
# =============================================================================

class IngestDataRequest(Request):
    # Request structure is internal to partners
    pass


# =============================================================================
# Ingestion Summary Requests
# =============================================================================

class GetIngestionSummaryDataRequestBody(G2PRequestBody):
    request_payload: EmptyIngestionRequestPayload


class GetIngestionSummaryDataRequest(G2PRequest):
    request_body: GetIngestionSummaryDataRequestBody


# =============================================================================
# Ingestion Search Requests
# =============================================================================

class SearchIngestionDataRequestBody(G2PRequestBody):
    request_payload: EmptyIngestionRequestPayload


class SearchIngestionDataRequest(G2PRequest):
    request_body: SearchIngestionDataRequestBody


# =============================================================================
# Ingestion Data Payload Requests
# =============================================================================

class GetIngestionDataPayloadRequestBody(G2PRequestBody):
    request_payload: GetIngestionDataRequestPayload


class GetIngestionDataPayloadRequest(G2PRequest):
    request_body: GetIngestionDataPayloadRequestBody


# =============================================================================
# IncomingPartner Request Schemas
# =============================================================================

class IncomingPartnerRequestBody(G2PRequestBody):
    request_payload: IncomingPartnerPayload


class IncomingPartnerRequest(G2PRequest):
    request_body: IncomingPartnerRequestBody


class IncomingPartnerUpdateRequestBody(G2PRequestBody):
    request_payload: IncomingPartnerUpdatePayload


class IncomingPartnerUpdateRequest(G2PRequest):
    request_body: IncomingPartnerUpdateRequestBody


# =============================================================================
# IncomingModelKeyPath Request Schemas
# =============================================================================

class IncomingModelKeyPathRequestBody(G2PRequestBody):
    request_payload: IncomingModelKeyPathPayload


class IncomingModelKeyPathRequest(G2PRequest):
    request_body: IncomingModelKeyPathRequestBody


class IncomingModelKeyPathIdRequestBody(G2PRequestBody):
    request_payload: GetIncomingKeyPathPayload


class IncomingModelKeyPathIdRequest(G2PRequest):
    request_body: IncomingModelKeyPathIdRequestBody


class IncomingModelKeyPathUpdateRequestBody(G2PRequestBody):
    request_payload: IncomingModelKeyPathUpdatePayload


class IncomingModelKeyPathUpdateRequest(G2PRequest):
    request_body: IncomingModelKeyPathUpdateRequestBody


class GetAllIncomingKeyPathsRequestBody(G2PRequestBody):
    request_payload: EmptyIngestionRequestPayload


class GetAllIncomingKeyPathsRequest(G2PRequest):
    request_body: GetAllIncomingKeyPathsRequestBody


# =============================================================================
# IncomingModelSemanticPattern Request Schemas
# =============================================================================

class IncomingModelSemanticPatternRequestBody(G2PRequestBody):
    request_payload: IncomingModelSemanticPatternPayload


class IncomingModelSemanticPatternRequest(G2PRequest):
    request_body: IncomingModelSemanticPatternRequestBody


class IncomingModelSemanticPatternIdRequestBody(G2PRequestBody):
    request_payload: GetIncomingSemanticPatternPayload


class IncomingModelSemanticPatternIdRequest(G2PRequest):
    request_body: IncomingModelSemanticPatternIdRequestBody


class IncomingModelSemanticPatternUpdateRequestBody(G2PRequestBody):
    request_payload: IncomingModelSemanticPatternUpdatePayload


class IncomingModelSemanticPatternUpdateRequest(G2PRequest):
    request_body: IncomingModelSemanticPatternUpdateRequestBody


class GetAllIncomingSemanticPatternsRequestBody(G2PRequestBody):
    request_payload: EmptyIngestionRequestPayload


class GetAllIncomingSemanticPatternsRequest(G2PRequest):
    request_body: GetAllIncomingSemanticPatternsRequestBody


# =============================================================================
# IncomingModelRegisterSemanticPattern Request Schemas
# =============================================================================


class IncomingModelRegisterSemanticPatternRequestBody(G2PRequestBody):
    request_payload: IncomingModelRegisterSemanticPatternPayload


class IncomingModelRegisterSemanticPatternRequest(G2PRequest):
    request_body: IncomingModelRegisterSemanticPatternRequestBody


class IncomingModelRegisterSemanticPatternIdRequestBody(G2PRequestBody):
    request_payload: GetIncomingRegisterSemanticPatternPayload


class IncomingModelRegisterSemanticPatternIdRequest(G2PRequest):
    request_body: IncomingModelRegisterSemanticPatternIdRequestBody


class IncomingModelRegisterSemanticPatternUpdateRequestBody(G2PRequestBody):
    request_payload: IncomingModelRegisterSemanticPatternUpdatePayload


class IncomingModelRegisterSemanticPatternUpdateRequest(G2PRequest):
    request_body: IncomingModelRegisterSemanticPatternUpdateRequestBody


class GetAllIncomingRegisterSemanticPatternsRequestBody(G2PRequestBody):
    request_payload: EmptyIngestionRequestPayload


class GetAllIncomingRegisterSemanticPatternsRequest(G2PRequest):
    request_body: GetAllIncomingRegisterSemanticPatternsRequestBody


# =============================================================================
# IncomingTemplate Request Schemas
# =============================================================================

class IncomingTemplateRequestBody(G2PRequestBody):
    request_payload: IncomingTemplatePayload


class IncomingTemplateRequest(G2PRequest):
    request_body: IncomingTemplateRequestBody


class IncomingTemplateIdRequestBody(G2PRequestBody):
    request_payload: GetIncomingTemplatePayload


class IncomingTemplateIdRequest(G2PRequest):
    request_body: IncomingTemplateIdRequestBody


class IncomingTemplateUpdateRequestBody(G2PRequestBody):
    request_payload: IncomingTemplateUpdatePayload


class IncomingTemplateUpdateRequest(G2PRequest):
    request_body: IncomingTemplateUpdateRequestBody


class GetAllIncomingTemplatesRequestBody(G2PRequestBody):
    request_payload: EmptyIngestionRequestPayload


class GetAllIncomingTemplatesRequest(G2PRequest):
    request_body: GetAllIncomingTemplatesRequestBody


# =============================================================================
# DataModel Request Schemas
# =============================================================================

class DataModelRequestBody(G2PRequestBody):
    request_payload: DataModelPayload


class DataModelRequest(G2PRequest):
    request_body: DataModelRequestBody


class DataModelIdRequestBody(G2PRequestBody):
    request_payload: DataModelIdPayload


class DataModelIdRequest(G2PRequest):
    request_body: DataModelIdRequestBody


class DataModelUpdateRequestBody(G2PRequestBody):
    request_payload: DataModelUpdatePayload


class DataModelUpdateRequest(G2PRequest):
    request_body: DataModelUpdateRequestBody


class GetAllDataModelsRequestBody(G2PRequestBody):
    request_payload: EmptyIngestionRequestPayload


class GetAllDataModelsRequest(G2PRequest):
    request_body: GetAllDataModelsRequestBody


class ChangeResponseTemplateFileRequestBody(G2PRequestBody):
    request_payload: ChangeResponseTemplateFilePayload


class ChangeResponseTemplateFileRequest(G2PRequest):
    request_body: ChangeResponseTemplateFileRequestBody


class ChangeActiveStatusRequestBody(G2PRequestBody):
    request_payload: ChangeActiveStatusPayload


class ChangeActiveStatusRequest(G2PRequest):
    request_body: ChangeActiveStatusRequestBody


# =============================================================================
# SubscriptionActivityLog Request Schemas
# =============================================================================

class SubscriptionActivityLogRequestBody(G2PRequestBody):
    request_payload: SubscriptionActivityLogPayload


class SubscriptionActivityLogRequest(G2PRequest):
    request_body: SubscriptionActivityLogRequestBody


class GetAllSubscriptionActivityLogsRequestBody(G2PRequestBody):
    request_payload: EmptyIngestionRequestPayload


class GetAllSubscriptionActivityLogsRequest(G2PRequest):
    request_body: GetAllSubscriptionActivityLogsRequestBody

# =============================================================================
# G2P Input Mechanism Request Schemas
# =============================================================================

class G2PInputMechanismRequestBody(G2PRequestBody):
    request_payload: G2PInputMechanismPayload


class G2PInputMechanismRequest(G2PRequest):
    request_body: G2PInputMechanismRequestBody
