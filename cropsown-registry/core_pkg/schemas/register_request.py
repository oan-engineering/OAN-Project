from openg2p_fastapi_common.schemas import (
    G2PRequest,
    G2PRequestBody
)
from .register_payload import (
    ChangeRequestRequestPayload,
    GetLanguageRequestPayload,
    SaveSubmissionDraftRequestPayload,
    FinalizeSubmissionRequestPayload,
    ApproveRejectSubmissionRequestPayload,
    GetSubmissionRequestPayload,
    SearchInSubmissionRequestPayload,
    GetChangeRequestsForSubmissionRequestPayload,
    GetNumberOfPendingChangeRequestsForSubmissionRequestPayload,
    GetIntakeFormsForRegisterRequestPayload,
    GetIntakeFormMetadataRequestPayload,
    AddVerificationPayload,
    EmptyRequestPayload,
    ChildRegisterRequestPayload,
    SearchRegisterRequestPayload,
    SearchChangeRequestRequestPayload,
    GetChildRegistersRequestPayload,
    GetMasterRegisterRequestPayload,
    GetNumberOfVersionsRequestPayload,
    GetRecordHistoryRequestPayload,
    GetVersionDatesRequestPayload,
    GetChangesForDateRequestPayload,
    GetNumberOfPendingChangeRequestsRequestPayload,
    GetNumberOfCrossRegisterChangesRequestPayload,
    GetCrossRegisterChangesRequestPayload,
    GetChangeRequestsRequestPayload,
    GetChangeRequestRequestPayload,
    GetSubjectRecordRequestPayload,
    GetVerificationsRequestPayload,
    GetDeduplicationRegisterResultsRequestPayload,
    GetDeduplicationChangerequestResultsRequestPayload,
    GetRegisterSchemaRequestPayload,
    GetRegisterFieldsRequestPayload,
    GetRegisterSectionsRequestPayload,
    GetRegisterTabSectionsRequestPayload,
    GetRegisterTabsRequestPayload,
    AddRegisterTabRequestPayload,
    DeleteRegisterTabRequestPayload,
    EditRegisterTabRequestPayload,
    GetRegisterSectionRequestPayload,
    AddRegisterSectionRequestPayload,
    DeleteRegisterSectionRequestPayload,
    GetRegisterSectionUISchemaRequestPayload,
    UpdateRegisterSectionRequestPayload,
    UpdateRegisterSectionUISchemaRequestPayload,
    CreateRegisterRequestPayload,
    EditRegisterRequestPayload,
    DeleteRegisterRequestPayload,
    UpdateRegisterSchemaRequestPayload,
    UpdateDedupIsEnabledRequestPayload,
    UpdateDedupThresholdScoreRequestPayload,
    UpdateDeduplicationSchemaRequestPayload,
    UpdateSearchResultSchemaRequestPayload,
    GetSectionRecordsRequestPayload,
    GetRegisterTabRecordsRequestPayload,
    CreateRegistryConfigurationRequestPayload,
    UpdateRegistryConfigurationRequestPayload,
    CreateThemeRequestPayload,
    RemoveThemeRequestPayload,
    UpdateThemeValuesRequestPayload,
    GetThemeValuesRequestPayload,
    CreateLanguageRequestPayload,
    UpdateLanguageRequestPayload,
    RemoveLanguageRequestPayload,
    GetAttributesRequestPayload,
    GetAttributeRequestPayload,
    CreateAttributeRequestPayload,
    UpdateAttributeRequestPayload,
    DeleteAttributeRequestPayload,
    GetAttributeValuesRequestPayload,
    CreateAttributeValueRequestPayload,
    UpdateAttributeValueRequestPayload,
    DeleteAttributeValueRequestPayload,
    GetAllowedParentsForChildSectionRequestPayload,
)


# =============================================================================
# Change Request Request Schemas
# =============================================================================

class ChangeRequestRequestBody(G2PRequestBody):
    request_payload: ChangeRequestRequestPayload


class ChangeRequestRequest(G2PRequest):
    request_body: ChangeRequestRequestBody

# =============================================================================
# Intake Form Request Schemas
# =============================================================================
class SaveSubmissionDraftRequestBody(G2PRequestBody):
    request_payload: SaveSubmissionDraftRequestPayload


class SaveSubmissionDraftRequest(G2PRequest):
    request_body: SaveSubmissionDraftRequestBody


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


class GetChangeRequestsForSubmissionRequestBody(G2PRequestBody):
    request_payload: GetChangeRequestsForSubmissionRequestPayload


class GetChangeRequestsForSubmissionRequest(G2PRequest):
    request_body: GetChangeRequestsForSubmissionRequestBody


class GetNumberOfPendingChangeRequestsForSubmissionRequestBody(G2PRequestBody):
    request_payload: GetNumberOfPendingChangeRequestsForSubmissionRequestPayload


class GetNumberOfPendingChangeRequestsForSubmissionRequest(G2PRequest):
    request_body: GetNumberOfPendingChangeRequestsForSubmissionRequestBody


class GetIntakeFormsForRegisterRequestBody(G2PRequestBody):
    request_payload: GetIntakeFormsForRegisterRequestPayload


class GetIntakeFormsForRegisterRequest(G2PRequest):
    request_body: GetIntakeFormsForRegisterRequestBody


class GetIntakeFormMetadataRequestBody(G2PRequestBody):
    request_payload: GetIntakeFormMetadataRequestPayload


class GetIntakeFormMetadataRequest(G2PRequest):
    request_body: GetIntakeFormMetadataRequestBody


# =============================================================================
# Empty Request Schemas
# =============================================================================

class EmptyRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class EmptyRequest(G2PRequest):
    request_body: EmptyRequestBody


# =============================================================================
# Register Summary Request Schemas
# =============================================================================

class GetRegisterSummaryDataRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetRegisterSummaryDataRequest(G2PRequest):
    request_body: GetRegisterSummaryDataRequestBody


class GetIntakeFormSubmissionsSummaryRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetIntakeFormSubmissionsSummaryRequest(G2PRequest):
    request_body: GetIntakeFormSubmissionsSummaryRequestBody


# =============================================================================
# Change Request Summary Request Schemas
# =============================================================================

class GetChangeRequestSummaryDataRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetChangeRequestSummaryDataRequest(G2PRequest):
    request_body: GetChangeRequestSummaryDataRequestBody


# =============================================================================
# Get All Registers Request Schemas
# =============================================================================

class GetAllRegistersRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetAllRegistersRequest(G2PRequest):
    request_body: GetAllRegistersRequestBody


# =============================================================================
# Get Dashboard Registers Request Schemas
# =============================================================================

class GetDashboardRegistersRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetDashboardRegistersRequest(G2PRequest):
    request_body: GetDashboardRegistersRequestBody


# =============================================================================
# Child Register Request Schemas
# =============================================================================

class ChildRegisterRequestBody(G2PRequestBody):
    request_payload: ChildRegisterRequestPayload


class ChildRegisterRequest(G2PRequest):
    request_body: ChildRegisterRequestBody


# =============================================================================
# Search Register Request Schemas
# =============================================================================

class SearchRegisterRequestBody(G2PRequestBody):
    request_payload: SearchRegisterRequestPayload


class SearchRegisterRequest(G2PRequest):
    request_body: SearchRegisterRequestBody


# =============================================================================
# Search Change Request Request Schemas
# =============================================================================

class SearchChangeRequestRequestBody(G2PRequestBody):
    request_payload: SearchChangeRequestRequestPayload


class SearchChangeRequestRequest(G2PRequest):
    request_body: SearchChangeRequestRequestBody


# =============================================================================
# Get Child Registers Request Schemas
# =============================================================================

class GetChildRegistersRequestBody(G2PRequestBody):
    request_payload: GetChildRegistersRequestPayload


class GetChildRegistersRequest(G2PRequest):
    request_body: GetChildRegistersRequestBody


# =============================================================================
# Get Master Register Request Schemas
# =============================================================================

class GetMasterRegisterRequestBody(G2PRequestBody):
    request_payload: GetMasterRegisterRequestPayload


class GetMasterRegisterRequest(G2PRequest):
    request_body: GetMasterRegisterRequestBody


# =============================================================================
# Get Number Of Versions Request Schemas
# =============================================================================

class GetNumberOfVersionsRequestBody(G2PRequestBody):
    request_payload: GetNumberOfVersionsRequestPayload


class GetNumberOfVersionsRequest(G2PRequest):
    request_body: GetNumberOfVersionsRequestBody


# =============================================================================
# Get Record History Request Schemas
# =============================================================================

class GetRecordHistoryRequestBody(G2PRequestBody):
    request_payload: GetRecordHistoryRequestPayload


class GetRecordHistoryRequest(G2PRequest):
    request_body: GetRecordHistoryRequestBody


# =============================================================================
# Get Version Dates Request Schemas
# =============================================================================

class GetVersionDatesRequestBody(G2PRequestBody):
    request_payload: GetVersionDatesRequestPayload


class GetVersionDatesRequest(G2PRequest):
    request_body: GetVersionDatesRequestBody


# =============================================================================
# Get Changes For Date Request Schemas
# =============================================================================

class GetChangesForDateRequestBody(G2PRequestBody):
    request_payload: GetChangesForDateRequestPayload


class GetChangesForDateRequest(G2PRequest):
    request_body: GetChangesForDateRequestBody


# =============================================================================
# Get Number Of Pending Change Requests Request Schemas
# =============================================================================

class GetNumberOfPendingChangeRequestsRequestBody(G2PRequestBody):
    request_payload: GetNumberOfPendingChangeRequestsRequestPayload


class GetNumberOfPendingChangeRequestsRequest(G2PRequest):
    request_body: GetNumberOfPendingChangeRequestsRequestBody


# =============================================================================
# Get Number Of Cross Register Changes Request Schemas
# =============================================================================

class GetNumberOfCrossRegisterChangesRequestBody(G2PRequestBody):
    request_payload: GetNumberOfCrossRegisterChangesRequestPayload


class GetNumberOfCrossRegisterChangesRequest(G2PRequest):
    request_body: GetNumberOfCrossRegisterChangesRequestBody


# =============================================================================
# Get Cross Register Changes Request Schemas
# =============================================================================

class GetCrossRegisterChangesRequestBody(G2PRequestBody):
    request_payload: GetCrossRegisterChangesRequestPayload


class GetCrossRegisterChangesRequest(G2PRequest):
    request_body: GetCrossRegisterChangesRequestBody


# =============================================================================
# Get Change Requests Request Schemas
# =============================================================================

class GetChangeRequestsRequestBody(G2PRequestBody):
    request_payload: GetChangeRequestsRequestPayload


class GetChangeRequestsRequest(G2PRequest):
    request_body: GetChangeRequestsRequestBody


# =============================================================================
# Get Change Request Request Schemas
# =============================================================================

class GetChangeRequestRequestBody(G2PRequestBody):
    request_payload: GetChangeRequestRequestPayload


class GetChangeRequestRequest(G2PRequest):
    request_body: GetChangeRequestRequestBody


# =============================================================================
# Get Subject Record Request Schemas
# =============================================================================

class GetSubjectRecordRequestBody(G2PRequestBody):
    request_payload: GetSubjectRecordRequestPayload


class GetSubjectRecordRequest(G2PRequest):
    request_body: GetSubjectRecordRequestBody


# =============================================================================
# Get Verifications Request Schemas
# =============================================================================

class GetVerificationsRequestBody(G2PRequestBody):
    request_payload: GetVerificationsRequestPayload


class GetVerificationsRequest(G2PRequest):
    request_body: GetVerificationsRequestBody


# =============================================================================
# Get Deduplication Register Results Request Schemas
# =============================================================================

class GetDeduplicationRegisterResultsRequestBody(G2PRequestBody):
    request_payload: GetDeduplicationRegisterResultsRequestPayload


class GetDeduplicationRegisterResultsRequest(G2PRequest):
    request_body: GetDeduplicationRegisterResultsRequestBody


# =============================================================================
# Get Deduplication Change Request Results Request Schemas
# =============================================================================

class GetDeduplicationChangerequestResultsRequestBody(G2PRequestBody):
    request_payload: GetDeduplicationChangerequestResultsRequestPayload


class GetDeduplicationChangerequestResultsRequest(G2PRequest):
    request_body: GetDeduplicationChangerequestResultsRequestBody


# =============================================================================
# Add Verification Request Schemas
# =============================================================================

class AddVerificationRequestBody(G2PRequestBody):
    request_payload: AddVerificationPayload


class AddVerificationRequest(G2PRequest):
    request_body: AddVerificationRequestBody


# =============================================================================
# Get Register Schema Request Schemas
# =============================================================================

class GetRegisterSchemaRequestBody(G2PRequestBody):
    request_payload: GetRegisterSchemaRequestPayload


class GetRegisterSchemaRequest(G2PRequest):
    request_body: GetRegisterSchemaRequestBody


class GetRegisterFieldsRequestBody(G2PRequestBody):
    request_payload: GetRegisterFieldsRequestPayload


class GetRegisterFieldsRequest(G2PRequest):
    request_body: GetRegisterFieldsRequestBody


# =============================================================================
# Get Register Sections Request Schemas
# =============================================================================

class GetRegisterSectionsRequestBody(G2PRequestBody):
    request_payload: GetRegisterSectionsRequestPayload


class GetRegisterSectionsRequest(G2PRequest):
    request_body: GetRegisterSectionsRequestBody


# =============================================================================
# Get Register Tab Sections Request Schemas
# =============================================================================

class GetRegisterTabSectionsRequestBody(G2PRequestBody):
    request_payload: GetRegisterTabSectionsRequestPayload


class GetRegisterTabSectionsRequest(G2PRequest):
    request_body: GetRegisterTabSectionsRequestBody


# =============================================================================
# Get Register Tabs Request Schemas
# =============================================================================

class GetRegisterTabsRequestBody(G2PRequestBody):
    request_payload: GetRegisterTabsRequestPayload


class GetRegisterTabsRequest(G2PRequest):
    request_body: GetRegisterTabsRequestBody


# =============================================================================
# Add Register Tab Request Schemas
# =============================================================================

class AddRegisterTabRequestBody(G2PRequestBody):
    request_payload: AddRegisterTabRequestPayload


class AddRegisterTabRequest(G2PRequest):
    request_body: AddRegisterTabRequestBody


# =============================================================================
# Delete Register Tab Request Schemas
# =============================================================================

class DeleteRegisterTabRequestBody(G2PRequestBody):
    request_payload: DeleteRegisterTabRequestPayload


class DeleteRegisterTabRequest(G2PRequest):
    request_body: DeleteRegisterTabRequestBody


# =============================================================================
# Edit Register Tab Request Schemas
# =============================================================================

class EditRegisterTabRequestBody(G2PRequestBody):
    request_payload: EditRegisterTabRequestPayload


class EditRegisterTabRequest(G2PRequest):
    request_body: EditRegisterTabRequestBody


# =============================================================================
# Get Register Section Request Schemas
# =============================================================================

class GetRegisterSectionRequestBody(G2PRequestBody):
    request_payload: GetRegisterSectionRequestPayload


class GetRegisterSectionRequest(G2PRequest):
    request_body: GetRegisterSectionRequestBody


# =============================================================================
# Add Register Section Request Schemas
# =============================================================================

class AddRegisterSectionRequestBody(G2PRequestBody):
    request_payload: AddRegisterSectionRequestPayload


class AddRegisterSectionRequest(G2PRequest):
    request_body: AddRegisterSectionRequestBody


# =============================================================================
# Delete Register Section Request Schemas
# =============================================================================

class DeleteRegisterSectionRequestBody(G2PRequestBody):
    request_payload: DeleteRegisterSectionRequestPayload


class DeleteRegisterSectionRequest(G2PRequest):
    request_body: DeleteRegisterSectionRequestBody


# =============================================================================
# Get Register Section UI Schema Request Schemas
# =============================================================================

class GetRegisterSectionUISchemaRequestBody(G2PRequestBody):
    request_payload: GetRegisterSectionUISchemaRequestPayload


class GetRegisterSectionUISchemaRequest(G2PRequest):
    request_body: GetRegisterSectionUISchemaRequestBody


# =============================================================================
# Update Register Section Request Schemas
# =============================================================================

class UpdateRegisterSectionRequestBody(G2PRequestBody):
    request_payload: UpdateRegisterSectionRequestPayload


class UpdateRegisterSectionRequest(G2PRequest):
    request_body: UpdateRegisterSectionRequestBody


# =============================================================================
# Update Register Section UI Schema Request Schemas
# =============================================================================

class UpdateRegisterSectionUISchemaRequestBody(G2PRequestBody):
    request_payload: UpdateRegisterSectionUISchemaRequestPayload


class UpdateRegisterSectionUISchemaRequest(G2PRequest):
    request_body: UpdateRegisterSectionUISchemaRequestBody


# =============================================================================
# Create Register Request Schemas
# =============================================================================

class CreateRegisterRequestBody(G2PRequestBody):
    request_payload: CreateRegisterRequestPayload


class CreateRegisterRequest(G2PRequest):
    request_body: CreateRegisterRequestBody


# =============================================================================
# Edit Register Request Schemas
# =============================================================================

class EditRegisterRequestBody(G2PRequestBody):
    request_payload: EditRegisterRequestPayload


class EditRegisterRequest(G2PRequest):
    request_body: EditRegisterRequestBody


# =============================================================================
# Delete Register Request Schemas
# =============================================================================

class DeleteRegisterRequestBody(G2PRequestBody):
    request_payload: DeleteRegisterRequestPayload


class DeleteRegisterRequest(G2PRequest):
    request_body: DeleteRegisterRequestBody


# =============================================================================
# Update Register Schema Request Schemas
# =============================================================================

class UpdateRegisterSchemaRequestBody(G2PRequestBody):
    request_payload: UpdateRegisterSchemaRequestPayload


class UpdateRegisterSchemaRequest(G2PRequest):
    request_body: UpdateRegisterSchemaRequestBody


# =============================================================================
# Deduplication Configuration Request Schemas
# =============================================================================

class UpdateDedupIsEnabledRequestBody(G2PRequestBody):
    request_payload: UpdateDedupIsEnabledRequestPayload


class UpdateDedupIsEnabledRequest(G2PRequest):
    request_body: UpdateDedupIsEnabledRequestBody


class UpdateDedupThresholdScoreRequestBody(G2PRequestBody):
    request_payload: UpdateDedupThresholdScoreRequestPayload


class UpdateDedupThresholdScoreRequest(G2PRequest):
    request_body: UpdateDedupThresholdScoreRequestBody


class UpdateDeduplicationSchemaRequestBody(G2PRequestBody):
    request_payload: UpdateDeduplicationSchemaRequestPayload


class UpdateDeduplicationSchemaRequest(G2PRequest):
    request_body: UpdateDeduplicationSchemaRequestBody


class UpdateSearchResultSchemaRequestBody(G2PRequestBody):
    request_payload: UpdateSearchResultSchemaRequestPayload


class UpdateSearchResultSchemaRequest(G2PRequest):
    request_body: UpdateSearchResultSchemaRequestBody


# =============================================================================
# Get Section Records Request Schemas
# =============================================================================

class GetSectionRecordsRequestBody(G2PRequestBody):
    request_payload: GetSectionRecordsRequestPayload


class GetSectionRecordsRequest(G2PRequest):
    request_body: GetSectionRecordsRequestBody


# =============================================================================
# Get Register Tab Records Request Schemas
# =============================================================================

class GetRegisterTabRecordsRequestBody(G2PRequestBody):
    request_payload: GetRegisterTabRecordsRequestPayload


class GetRegisterTabRecordsRequest(G2PRequest):
    request_body: GetRegisterTabRecordsRequestBody


# =============================================================================
# Registry Configuration Request Schemas
# =============================================================================

class CreateRegistryConfigurationRequestBody(G2PRequestBody):
    request_payload: CreateRegistryConfigurationRequestPayload


class CreateRegistryConfigurationRequest(G2PRequest):
    request_body: CreateRegistryConfigurationRequestBody


class GetRegistryConfigurationRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetRegistryConfigurationRequest(G2PRequest):
    request_body: GetRegistryConfigurationRequestBody


class UpdateRegistryConfigurationRequestBody(G2PRequestBody):
    request_payload: UpdateRegistryConfigurationRequestPayload


class UpdateRegistryConfigurationRequest(G2PRequest):
    request_body: UpdateRegistryConfigurationRequestBody


class GetAllThemesRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetAllThemesRequest(G2PRequest):
    request_body: GetAllThemesRequestBody


class CreateThemeRequestBody(G2PRequestBody):
    request_payload: CreateThemeRequestPayload


class CreateThemeRequest(G2PRequest):
    request_body: CreateThemeRequestBody


class RemoveThemeRequestBody(G2PRequestBody):
    request_payload: RemoveThemeRequestPayload


class RemoveThemeRequest(G2PRequest):
    request_body: RemoveThemeRequestBody


class UpdateThemeValuesRequestBody(G2PRequestBody):
    request_payload: UpdateThemeValuesRequestPayload


class UpdateThemeValuesRequest(G2PRequest):
    request_body: UpdateThemeValuesRequestBody


class GetThemeValuesRequestBody(G2PRequestBody):
    request_payload: GetThemeValuesRequestPayload


class GetThemeValuesRequest(G2PRequest):
    request_body: GetThemeValuesRequestBody


class GetLanguageRequestBody(G2PRequestBody):
    request_payload: GetLanguageRequestPayload


class GetLanguageRequest(G2PRequest):
    request_body: GetLanguageRequestBody

    
class GetAllLanguagesRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetAllLanguagesRequest(G2PRequest):
    request_body: GetAllLanguagesRequestBody


class CreateLanguageRequestBody(G2PRequestBody):
    request_payload: CreateLanguageRequestPayload


class CreateLanguageRequest(G2PRequest):
    request_body: CreateLanguageRequestBody


class UpdateLanguageRequestBody(G2PRequestBody):
    request_payload: UpdateLanguageRequestPayload


class UpdateLanguageRequest(G2PRequest):
    request_body: UpdateLanguageRequestBody


class RemoveLanguageRequestBody(G2PRequestBody):
    request_payload: RemoveLanguageRequestPayload


class RemoveLanguageRequest(G2PRequest):
    request_body: RemoveLanguageRequestBody


# =============================================================================
# Change Request Additional Request Schemas
# =============================================================================

class GetNumberOfRequestsPendingRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetNumberOfRequestsPendingRequest(G2PRequest):
    request_body: GetNumberOfRequestsPendingRequestBody


class GetEarliestPendingChangeRequestRequestBody(G2PRequestBody):
    request_payload: EmptyRequestPayload


class GetEarliestPendingChangeRequestRequest(G2PRequest):
    request_body: GetEarliestPendingChangeRequestRequestBody


# =============================================================================
# Attribute Request Schemas
# =============================================================================

class GetAttributesRequestBody(G2PRequestBody):
    request_payload: GetAttributesRequestPayload


class GetAttributesRequest(G2PRequest):
    request_body: GetAttributesRequestBody


class GetAttributeRequestBody(G2PRequestBody):
    request_payload: GetAttributeRequestPayload


class GetAttributeRequest(G2PRequest):
    request_body: GetAttributeRequestBody


class CreateAttributeRequestBody(G2PRequestBody):
    request_payload: CreateAttributeRequestPayload


class CreateAttributeRequest(G2PRequest):
    request_body: CreateAttributeRequestBody


class UpdateAttributeRequestBody(G2PRequestBody):
    request_payload: UpdateAttributeRequestPayload


class UpdateAttributeRequest(G2PRequest):
    request_body: UpdateAttributeRequestBody


class DeleteAttributeRequestBody(G2PRequestBody):
    request_payload: DeleteAttributeRequestPayload


class DeleteAttributeRequest(G2PRequest):
    request_body: DeleteAttributeRequestBody


class GetAttributeValuesRequestBody(G2PRequestBody):
    request_payload: GetAttributeValuesRequestPayload


class GetAttributeValuesRequest(G2PRequest):
    request_body: GetAttributeValuesRequestBody


class CreateAttributeValueRequestBody(G2PRequestBody):
    request_payload: CreateAttributeValueRequestPayload


class CreateAttributeValueRequest(G2PRequest):
    request_body: CreateAttributeValueRequestBody


class UpdateAttributeValueRequestBody(G2PRequestBody):
    request_payload: UpdateAttributeValueRequestPayload


class UpdateAttributeValueRequest(G2PRequest):
    request_body: UpdateAttributeValueRequestBody


class DeleteAttributeValueRequestBody(G2PRequestBody):
    request_payload: DeleteAttributeValueRequestPayload


class DeleteAttributeValueRequest(G2PRequest):
    request_body: DeleteAttributeValueRequestBody


# =============================================================================
# Allowed Parents For Child Section Request Schemas
# =============================================================================

class GetAllowedParentsForChildSectionRequestBody(G2PRequestBody):
    request_payload: GetAllowedParentsForChildSectionRequestPayload


class GetAllowedParentsForChildSectionRequest(G2PRequest):
    request_body: GetAllowedParentsForChildSectionRequestBody
