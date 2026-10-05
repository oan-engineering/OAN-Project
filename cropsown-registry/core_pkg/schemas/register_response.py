from typing import Optional, List
from openg2p_fastapi_common.schemas import (
    G2PResponse,
    G2PResponseBody,
    G2PResponseHeader,
)
from .register_payload import (
    ChangeRequestResponsePayload, RegisterSummaryData, ChangeRequestSummaryData, RegisterData, AllRegistersRegisterData, ChildRegisterData,
    RegisterUITabData, SearchResultData, ChangeRequestSearchResultData,
    NumberOfVersionsData, NumberOfPendingChangeRequestsData, NumberOfCrossRegisterChangesData,
    CrossRegisterChangeRequestData, CrossRegisterChangesData,
    ChangeRequestData, ChangeRequestsData, ChangeRequestFlattenedData, RecordData, VerificationData, VerificationsData,
    AddVerificationPayload, DeduplicationRegisterResultsData,
    DeduplicationChangerequestResultsData, RegisterSchemaData, RegisterFieldsData, RegisterSectionData, RegisterSectionUISchemaData,
    RegisterTabRecordData,
    RegistryConfigurationData, NumberOfRequestsPendingData, EarliestPendingChangeRequestData,
    RegistryThemeData, RegistryThemeValueData, ThemeOperationData,
    RegistryLanguageData, LanguageOperationData,
    RecordHistoryData, RecordHistoryListData, VersionDatesData, VersionForDateData, VersionsForDateData,
    AttributeData, AttributeValueData, AllowedParentsData,
    CreateAttributeResponsePayload, UpdateAttributeResponsePayload, DeleteAttributeResponsePayload,
    CreateAttributeValueResponsePayload, UpdateAttributeValueResponsePayload, DeleteAttributeValueResponsePayload,
    SubmissionResponsePayload, IntakeFormSubmissionsSummaryData, NumberOfPendingChangeRequestsForSubmissionData
)


# =============================================================================
# Change Request Response Schemas
# =============================================================================

class ChangeRequestResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestResponsePayload] = None


class ChangeRequestResponse(G2PResponse):
    response_body: Optional[ChangeRequestResponseBody] = None

# =============================================================================
# Intake Form Response Schemas
# =============================================================================

class SubmissionResponseBody(G2PResponseBody):
    response_payload: Optional[SubmissionResponsePayload] = None


class SubmissionResponse(G2PResponse):
    response_body: Optional[SubmissionResponseBody] = None


class SubmissionSearchResultsResponseBody(G2PResponseBody):
    response_payload: Optional[List[SubmissionResponsePayload]] = None


class SubmissionSearchResultsResponse(G2PResponse):
    response_body: Optional[SubmissionSearchResultsResponseBody] = None


class IntakeFormsForRegisterResponseBody(G2PResponseBody):
    response_payload: Optional[List[RegisterUITabData]] = None


class IntakeFormsForRegisterResponse(G2PResponse):
    response_body: Optional[IntakeFormsForRegisterResponseBody] = None


class IntakeFormMetadataResponseBody(G2PResponseBody):
    response_payload: Optional[List[RegisterSectionData]] = None


class IntakeFormMetadataResponse(G2PResponse):
    response_body: Optional[IntakeFormMetadataResponseBody] = None


class IntakeFormSubmissionsSummaryResponseBody(G2PResponseBody):
    response_payload: Optional[IntakeFormSubmissionsSummaryData] = None


class IntakeFormSubmissionsSummaryResponse(G2PResponse):
    response_body: Optional[IntakeFormSubmissionsSummaryResponseBody] = None


class NumberOfPendingChangeRequestsForSubmissionResponseBody(G2PResponseBody):
    response_payload: Optional[NumberOfPendingChangeRequestsForSubmissionData] = None


class NumberOfPendingChangeRequestsForSubmissionResponse(G2PResponse):
    response_body: Optional[NumberOfPendingChangeRequestsForSubmissionResponseBody] = None



# =============================================================================
# Register Summary Data Response Schemas
# =============================================================================

class RegisterSummaryDataResponseBody(G2PResponseBody):
    response_payload: Optional[List[RegisterSummaryData]] = None


class RegisterSummaryDataResponse(G2PResponse):
    response_body: Optional[RegisterSummaryDataResponseBody] = None


# =============================================================================
# Change Request Summary Data Response Schemas
# =============================================================================

class ChangeRequestSummaryDataResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestSummaryData] = None


class ChangeRequestSummaryDataResponse(G2PResponse):
    response_body: Optional[ChangeRequestSummaryDataResponseBody] = None


# =============================================================================
# All Registers Response Schemas
# =============================================================================

class AllRegistersResponseBody(G2PResponseBody):
    response_payload: Optional[List[AllRegistersRegisterData]] = None


class AllRegistersResponse(G2PResponse):
    response_body: Optional[AllRegistersResponseBody] = None


# =============================================================================
# Dashboard Registers Response Schemas
# =============================================================================

class DashboardRegistersResponseBody(G2PResponseBody):
    response_payload: Optional[List[RegisterData]] = None


class DashboardRegistersResponse(G2PResponse):
    response_body: Optional[DashboardRegistersResponseBody] = None


# =============================================================================
# Child Registers Response Schemas
# =============================================================================

class ChildRegistersResponseBody(G2PResponseBody):
    response_payload: Optional[List[ChildRegisterData]] = None


class ChildRegistersResponse(G2PResponse):
    response_body: Optional[ChildRegistersResponseBody] = None


# =============================================================================
# Search Results Response Schemas
# =============================================================================

class SearchResultsResponseBody(G2PResponseBody):
    response_payload: Optional[List[SearchResultData]] = None


class SearchResultsResponse(G2PResponse):
    response_body: Optional[SearchResultsResponseBody] = None


# =============================================================================
# Change Request Search Results Response Schemas
# =============================================================================

class ChangeRequestSearchResultsResponseBody(G2PResponseBody):
    response_payload: Optional[List[ChangeRequestSearchResultData]] = None


class ChangeRequestSearchResultsResponse(G2PResponse):
    response_body: Optional[ChangeRequestSearchResultsResponseBody] = None


# =============================================================================
# Number Of Versions Response Schemas
# =============================================================================

class NumberOfVersionsResponseBody(G2PResponseBody):
    response_payload: Optional[NumberOfVersionsData] = None


class NumberOfVersionsResponse(G2PResponse):
    response_body: Optional[NumberOfVersionsResponseBody] = None


# =============================================================================
# Record History Data Response Schemas
# =============================================================================

class RecordHistoryDataResponseBody(G2PResponseBody):
    response_payload: Optional["RecordHistoryListData"] = None


class RecordHistoryDataResponse(G2PResponse):
    response_body: Optional[RecordHistoryDataResponseBody] = None


# =============================================================================
# Version Dates Data Response Schemas
# =============================================================================

class VersionDatesDataResponseBody(G2PResponseBody):
    response_payload: Optional["VersionDatesData"] = None


class VersionDatesDataResponse(G2PResponse):
    response_body: Optional[VersionDatesDataResponseBody] = None


# =============================================================================
# Changes For Date Data Response Schemas
# =============================================================================

class ChangesForDateDataResponseBody(G2PResponseBody):
    response_payload: Optional[List["VersionsForDateData"]] = None


class ChangesForDateDataResponse(G2PResponse):
    response_body: Optional[ChangesForDateDataResponseBody] = None


# =============================================================================
# Number Of Pending Change Requests Response Schemas
# =============================================================================

class NumberOfPendingChangeRequestsResponseBody(G2PResponseBody):
    response_payload: Optional[NumberOfPendingChangeRequestsData] = None


class NumberOfPendingChangeRequestsResponse(G2PResponse):
    response_body: Optional[NumberOfPendingChangeRequestsResponseBody] = None


# =============================================================================
# Number Of Cross Register Changes Response Schemas
# =============================================================================

class NumberOfCrossRegisterChangesResponseBody(G2PResponseBody):
    response_payload: Optional[NumberOfCrossRegisterChangesData] = None


class NumberOfCrossRegisterChangesResponse(G2PResponse):
    response_body: Optional[NumberOfCrossRegisterChangesResponseBody] = None


# =============================================================================
# Cross Register Changes Data Response Schemas
# =============================================================================

class CrossRegisterChangesDataResponseBody(G2PResponseBody):
    response_payload: Optional[CrossRegisterChangesData] = None


class CrossRegisterChangesDataResponse(G2PResponse):
    response_body: Optional[CrossRegisterChangesDataResponseBody] = None


# =============================================================================
# Change Request Data Response Schemas
# =============================================================================

class ChangeRequestDataResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestData] = None


class ChangeRequestDataResponse(G2PResponse):
    response_body: Optional[ChangeRequestDataResponseBody] = None


# =============================================================================
# Change Requests Data Response Schemas
# =============================================================================

class ChangeRequestsDataResponseBody(G2PResponseBody):
    response_payload: Optional[ChangeRequestsData] = None


class ChangeRequestsDataResponse(G2PResponse):
    response_body: Optional[ChangeRequestsDataResponseBody] = None


# =============================================================================
# Change Request Flattened Data Response Schemas
# =============================================================================

class ChangeRequestFlattenedDataResponseBody(G2PResponseBody):
    response_payload: Optional[List[ChangeRequestFlattenedData]] = None


class ChangeRequestFlattenedDataResponse(G2PResponse):
    response_body: Optional[ChangeRequestFlattenedDataResponseBody] = None


# =============================================================================
# Record Data Response Schemas
# =============================================================================

class RecordDataResponseBody(G2PResponseBody):
    response_payload: Optional[RecordData] = None


class RecordDataResponse(G2PResponse):
    response_body: Optional[RecordDataResponseBody] = None


# =============================================================================
# Verifications Data Response Schemas
# =============================================================================

class VerificationsDataResponseBody(G2PResponseBody):
    response_payload: Optional[VerificationsData] = None


class VerificationsDataResponse(G2PResponse):
    response_body: Optional[VerificationsDataResponseBody] = None


# =============================================================================
# Verification Data Response Schemas
# =============================================================================

class VerificationDataResponseBody(G2PResponseBody):
    response_payload: Optional[VerificationData] = None


class VerificationDataResponse(G2PResponse):
    response_body: Optional[VerificationDataResponseBody] = None


# =============================================================================
# Deduplication Register Results Data Response Schemas
# =============================================================================

class DeduplicationRegisterResultsDataResponseBody(G2PResponseBody):
    response_payload: Optional[DeduplicationRegisterResultsData] = None


class DeduplicationRegisterResultsDataResponse(G2PResponse):
    response_body: Optional[DeduplicationRegisterResultsDataResponseBody] = None


# =============================================================================
# Deduplication Change Request Results Data Response Schemas
# =============================================================================

class DeduplicationChangerequestResultsDataResponseBody(G2PResponseBody):
    response_payload: Optional[DeduplicationChangerequestResultsData] = None


class DeduplicationChangerequestResultsDataResponse(G2PResponse):
    response_body: Optional[DeduplicationChangerequestResultsDataResponseBody] = None


# =============================================================================
# Register Schema Data Response Schemas
# =============================================================================

class RegisterSchemaDataResponseBody(G2PResponseBody):
    response_payload: Optional[RegisterSchemaData] = None


class RegisterSchemaDataResponse(G2PResponse):
    response_body: Optional[RegisterSchemaDataResponseBody] = None


class RegisterFieldsDataResponseBody(G2PResponseBody):
    response_payload: Optional[RegisterFieldsData] = None


class RegisterFieldsDataResponse(G2PResponse):
    response_body: Optional[RegisterFieldsDataResponseBody] = None


# =============================================================================
# Register Data Response Schemas
# =============================================================================

class RegisterDataResponseBody(G2PResponseBody):
    response_payload: Optional[RegisterData] = None


class RegisterDataResponse(G2PResponse):
    response_body: Optional[RegisterDataResponseBody] = None


# =============================================================================
# Register Sections Data Response Schemas
# =============================================================================

class RegisterSectionsDataResponseBody(G2PResponseBody):
    response_payload: Optional[List[RegisterSectionData]] = None


class RegisterSectionsDataResponse(G2PResponse):
    response_body: Optional[RegisterSectionsDataResponseBody] = None


# =============================================================================
# Register Section Data Response Schemas
# =============================================================================

class RegisterSectionDataResponseBody(G2PResponseBody):
    response_payload: Optional[RegisterSectionData] = None


class RegisterSectionDataResponse(G2PResponse):
    response_body: Optional[RegisterSectionDataResponseBody] = None


# =============================================================================
# Register Section UI Schema Data Response Schemas
# =============================================================================

class RegisterSectionUISchemaDataResponseBody(G2PResponseBody):
    response_payload: Optional[RegisterSectionUISchemaData] = None


class RegisterSectionUISchemaDataResponse(G2PResponse):
    response_body: Optional[RegisterSectionUISchemaDataResponseBody] = None


# =============================================================================
# Register Tabs Data Response Schemas
# =============================================================================

class RegisterTabsDataResponseBody(G2PResponseBody):
    response_payload: Optional[List[RegisterUITabData]] = None


class RegisterTabsDataResponse(G2PResponse):
    response_body: Optional[RegisterTabsDataResponseBody] = None


# =============================================================================
# Register Tab Data Response Schemas
# =============================================================================

class RegisterTabDataResponseBody(G2PResponseBody):
    response_payload: Optional[RegisterUITabData] = None


class RegisterTabDataResponse(G2PResponse):
    response_body: Optional[RegisterTabDataResponseBody] = None


# =============================================================================
# Section Records Data Response Schemas
# =============================================================================

class SectionRecordsDataResponseBody(G2PResponseBody):
    response_payload: Optional[List[RecordData]] = None


class SectionRecordsDataResponse(G2PResponse):
    response_body: Optional[SectionRecordsDataResponseBody] = None


# =============================================================================
# Register Tab Records Data Response Schemas
# =============================================================================

class RegisterTabRecordsDataResponseBody(G2PResponseBody):
    response_payload: Optional[List[RegisterTabRecordData]] = None


class RegisterTabRecordsDataResponse(G2PResponse):
    response_body: Optional[RegisterTabRecordsDataResponseBody] = None



# =============================================================================
# Registry Configuration Response Schemas
# =============================================================================

class RegistryConfigurationDataResponseBody(G2PResponseBody):
    response_payload: Optional["RegistryConfigurationData"] = None


class RegistryConfigurationDataResponse(G2PResponse):
    response_body: Optional[RegistryConfigurationDataResponseBody] = None


class RegistryThemesResponseBody(G2PResponseBody):
    response_payload: Optional[List["RegistryThemeData"]] = None


class RegistryThemesResponse(G2PResponse):
    response_body: Optional[RegistryThemesResponseBody] = None


class ThemeOperationResponseBody(G2PResponseBody):
    response_payload: Optional["ThemeOperationData"] = None


class ThemeOperationResponse(G2PResponse):
    response_body: Optional[ThemeOperationResponseBody] = None


class RegistryThemeValuesResponseBody(G2PResponseBody):
    response_payload: Optional[List["RegistryThemeValueData"]] = None


class RegistryThemeValuesResponse(G2PResponse):
    response_body: Optional[RegistryThemeValuesResponseBody] = None


class RegistryLanguagesResponseBody(G2PResponseBody):
    response_payload: Optional[List["RegistryLanguageData"]] = None


class RegistryLanguagesResponse(G2PResponse):
    response_body: Optional[RegistryLanguagesResponseBody] = None


class LanguageOperationResponseBody(G2PResponseBody):
    response_payload: Optional["LanguageOperationData"] = None


class LanguageOperationResponse(G2PResponse):
    response_body: Optional[LanguageOperationResponseBody] = None


class RegistryLanguageResponseBody(G2PResponseBody):
    response_payload: Optional[RegistryLanguageData] = None


class RegistryLanguageResponse(G2PResponse):
    response_body: Optional[RegistryLanguageResponseBody] = None


# =============================================================================
# Change Request Additional Response Schemas
# =============================================================================

class NumberOfRequestsPendingResponseBody(G2PResponseBody):
    response_payload: Optional["NumberOfRequestsPendingData"] = None


class NumberOfRequestsPendingResponse(G2PResponse):
    response_body: Optional[NumberOfRequestsPendingResponseBody] = None


class EarliestPendingChangeRequestResponseBody(G2PResponseBody):
    response_payload: Optional["EarliestPendingChangeRequestData"] = None


class EarliestPendingChangeRequestResponse(G2PResponse):
    response_body: Optional[EarliestPendingChangeRequestResponseBody] = None


# =============================================================================
# Attribute Response Schemas
# =============================================================================

class GetAttributesResponseBody(G2PResponseBody):
    response_payload: List[AttributeData]


class GetAttributesResponse(G2PResponse):
    response_header: G2PResponseHeader
    response_body: GetAttributesResponseBody


class GetAttributeResponseBody(G2PResponseBody):
    response_payload: AttributeData


class GetAttributeResponse(G2PResponse):
    response_header: G2PResponseHeader
    response_body: GetAttributeResponseBody


class CreateAttributeResponseBody(G2PResponseBody):
    response_payload: CreateAttributeResponsePayload


class CreateAttributeResponse(G2PResponse):
    response_header: G2PResponseHeader
    response_body: CreateAttributeResponseBody


class UpdateAttributeResponseBody(G2PResponseBody):
    response_payload: UpdateAttributeResponsePayload


class UpdateAttributeResponse(G2PResponse):
    response_header: G2PResponseHeader
    response_body: UpdateAttributeResponseBody


class DeleteAttributeResponseBody(G2PResponseBody):
    response_payload: DeleteAttributeResponsePayload


class DeleteAttributeResponse(G2PResponse):
    response_header: G2PResponseHeader
    response_body: DeleteAttributeResponseBody


class GetAttributeValuesResponseBody(G2PResponseBody):
    response_payload: List[AttributeValueData]


class GetAttributeValuesResponse(G2PResponse):
    response_header: G2PResponseHeader
    response_body: GetAttributeValuesResponseBody


class CreateAttributeValueResponseBody(G2PResponseBody):
    response_payload: CreateAttributeValueResponsePayload


class CreateAttributeValueResponse(G2PResponse):
    response_header: G2PResponseHeader
    response_body: CreateAttributeValueResponseBody


class UpdateAttributeValueResponseBody(G2PResponseBody):
    response_payload: UpdateAttributeValueResponsePayload


class UpdateAttributeValueResponse(G2PResponse):
    response_header: G2PResponseHeader
    response_body: UpdateAttributeValueResponseBody


class DeleteAttributeValueResponseBody(G2PResponseBody):
    response_payload: DeleteAttributeValueResponsePayload


class DeleteAttributeValueResponse(G2PResponse):
    response_header: G2PResponseHeader
    response_body: DeleteAttributeValueResponseBody


# =============================================================================
# Allowed Parents For Child Section Response Schemas
# =============================================================================

class AllowedParentsDataResponseBody(G2PResponseBody):
    response_payload: Optional[AllowedParentsData] = None


class AllowedParentsDataResponse(G2PResponse):
    response_body: Optional[AllowedParentsDataResponseBody] = None
