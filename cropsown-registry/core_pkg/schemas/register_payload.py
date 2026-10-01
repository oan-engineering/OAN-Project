from typing import Optional, List, Any, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator, Field
from enum import Enum

from ..models import ApprovalStatusEnum
from .file_payload import DocumentAttachment, DocumentData


# =============================================================================
# Filter Types and Schemas (GraphQL-style filtering with security)
# =============================================================================

class FilterOperator(str, Enum):
    """Supported filter operators."""
    # Equality
    EQ = "eq"
    NEQ = "neq"
    # List
    IN = "in"
    NIN = "nin"
    # String
    CONTAINS = "contains"
    NCONTAINS = "ncontains"
    STARTS_WITH = "startsWith"
    ENDS_WITH = "endsWith"
    # Comparison
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    # Null
    IS_NULL = "isNull"


class FilterCondition(BaseModel):
    """
    Single field filter with operators.
    Supports GraphQL-style filtering like: {"field": {"eq": "value"}}
    """
    eq: Optional[Any] = None
    neq: Optional[Any] = None
    in_: Optional[List[Any]] = Field(default=None, alias="in")
    nin: Optional[List[Any]] = None
    contains: Optional[str] = None
    ncontains: Optional[str] = None
    startsWith: Optional[str] = None
    endsWith: Optional[str] = None
    gt: Optional[Any] = None
    gte: Optional[Any] = None
    lt: Optional[Any] = None
    lte: Optional[Any] = None
    isNull: Optional[bool] = None

    class Config:
        populate_by_name = True

    @model_validator(mode='after')
    def check_max_operators(self):
        """Security: Limit operators per field to prevent DoS."""
        MAX_OPERATORS = 3
        non_null_count = sum(
            1 for field_name in self.model_fields.keys()
            if getattr(self, field_name if field_name != 'in_' else 'in_') is not None
        )
        if non_null_count > MAX_OPERATORS:
            raise ValueError(f"Maximum {MAX_OPERATORS} operators per field allowed")
        return self


class FilterSchemaFieldOption(BaseModel):
    """Option for dropdown filter type."""
    value: str
    label: str


class FilterSchemaField(BaseModel):
    """
    Schema definition for a filterable field.
    This is stored in filter_schema and tells the frontend what filters are available.
    """
    field_name: str
    display_label: str
    filter_type: Literal["dropdown", "text", "date_range", "number_range", "boolean"]
    order: int
    allowed_operators: List[str]
    options: Optional[List[FilterSchemaFieldOption]] = None  # For dropdown with static options
    options_source: Optional[str] = None  # "distinct" to fetch from DB

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "field_name": "approval_status",
                    "display_label": "Status",
                    "filter_type": "dropdown",
                    "order": 1,
                    "allowed_operators": ["eq", "in"],
                    "options": [
                        {"value": "PENDING", "label": "Pending"},
                        {"value": "APPROVED", "label": "Approved"}
                    ]
                },
                {
                    "field_name": "date_of_birth",
                    "display_label": "Date of Birth",
                    "filter_type": "date_range",
                    "order": 2,
                    "allowed_operators": ["eq", "gte", "lte", "gt", "lt"]
                },
                {
                    "field_name": "first_name",
                    "display_label": "First Name",
                    "filter_type": "text",
                    "order": 3,
                    "allowed_operators": ["eq", "contains", "startsWith", "endsWith"]
                }
            ]
        }


# =============================================================================
# Base Register Payload
# =============================================================================

class RegisterPayload(BaseModel):
    pass


# =============================================================================
# Register Summary Data
# =============================================================================

class RegisterSummaryData(BaseModel):
    register_id: str
    register_mnemonic: str
    register_subject: Optional[str] = None
    has_image: bool
    register_icon: Optional[str] = None
    total_record_count: int


class ChangeRequestSummaryData(BaseModel):
    total_count: int
    approved_count: int
    pending_count: int


# =============================================================================
# Register Data
# =============================================================================

class RegisterData(BaseModel):
    register_id: str
    register_mnemonic: str
    register_subject: Optional[str] = None
    register_description: Optional[str] = None
    master_register_id: Optional[str] = None
    register_purpose: Optional[str] = None
    register_rank: Optional[int] = None
    register_icon: Optional[str] = None
    functional_id_generation_required: bool = False
    completion_score_required: bool = False
    outgest_applicable: bool = False
    requires_registrant_authentication: bool = False
    registrant_authentication_validity_days: Optional[int] = 730
    registrant_re_auth_warning_days_before: Optional[int] = 30


class AllRegistersRegisterData(RegisterData):
    """Extended RegisterData for get_all_registers API with additional fields"""
    master_register_mnemonic: Optional[str] = None
    has_data: bool = False
    # Additional fields from G2PRegisterDefinition
    register_purpose: Optional[str] = None
    program_id: Optional[str] = None
    program_mnemonic: Optional[str] = None
    register_rank: Optional[int] = None
    register_icon: Optional[str] = None
    has_image: bool = False
    dedup_is_enabled: bool = False
    dedup_threshold_score: Optional[float] = None
    functional_id_generation_required: bool = False
    completion_score_required: bool = False
    outgest_applicable: bool = False
    requires_registrant_authentication: bool = False
    registrant_authentication_validity_days: Optional[int] = 730
    registrant_re_auth_warning_days_before: Optional[int] = 30


class ChildRegisterData(BaseModel):
    register_id: str
    register_mnemonic: str
    register_subject: Optional[str] = None
    register_description: Optional[str] = None


class RegisterUITabData(BaseModel):
    tab_id: str
    register_id: str
    tab_label: str
    tab_order: int
    used_for_new_intake_form: bool = False
    no_of_verifications_required: int = 0
    intake_form_name: Optional[str] = None
    intake_form_description: Optional[str] = None
    intake_form_auto_approve: bool = False
    is_active: bool = True


# =============================================================================
# Display Field and Search Result Data
# =============================================================================

class DisplayField(BaseModel):
    field_name: str
    value: Optional[str] = None
    order: int


class SearchResultData(BaseModel):
    internal_record_id: str
    functional_record_id: Optional[str] = None
    link_internal_record_id: Optional[str] = None
    foundational_id: Optional[str] = None
    link_foundational_id: Optional[str] = None
    record_name: Optional[str] = None
    record_image_url: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    last_approved_at: Optional[str] = None
    last_approved_by: Optional[str] = None
    display_fields: Optional[List[DisplayField]] = None

    class Config:
        from_attributes: bool = True

class DeepSearchResultData(BaseModel):
    internal_record_id: str
    functional_record_id: Optional[str] = None
    link_internal_record_id: Optional[str] = None
    foundational_id: Optional[str] = None
    link_foundational_id: Optional[str] = None
    record_name: Optional[str] = None
    record_image_url: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    last_approved_at: Optional[str] = None
    last_approved_by: Optional[str] = None

    class Config:
        extra = "allow"
        from_attributes: bool = True


# =============================================================================
# Record Data
# =============================================================================

class RecordData(BaseModel):
    """
    Record data with flattened additional fields.
    Extra fields from the register implementation table are included at root level.
    """
    model_config = ConfigDict(extra="allow", from_attributes=True)
    
    actual_score: float = 0.0
    ideal_score: float = 0.0
    completion_score_required: bool = False
    documents: Optional[List[DocumentData]] = None



# =============================================================================
# Change Request Data
# =============================================================================

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
    # Stored in DB as JSON; historically dict, now typically a list of dict payloads
    change_payload: Optional[dict | List[dict]] = None

    class Config:
        from_attributes: bool = True


class BaseChangePayload(BaseModel):
    """Base change payload with dynamic fields."""
    pass


class ChangeActionEnum(str, Enum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    NO_CHANGE = "NO_CHANGE"


class RegisterRelationEnum(str, Enum):
    """Relationship type between a section's register and the queried register."""
    SELF = "SELF"
    DESCENDANT = "DESCENDANT"
    DESCENDANT_OF_A_REGISTER = "DESCENDANT_OF_A_REGISTER"  # Indirect descendant with REGISTER in between
    ANCESTOR = "ANCESTOR"
    PEER = "PEER"


class ChangePayload(BaseChangePayload):
    internal_record_id: Optional[str] = None
    edit_action: str = ChangeActionEnum.ADD.value
    class Config:
        from_attributes: bool = True
        extra = "allow"  # Allow extra fields to be preserved and accessible


class ChangeRequestRequestPayload(RegisterPayload):
    """Request payload for creating/updating change requests - sent from Partners"""
    register_id: Optional[str] = None
    register_mnemonic: Optional[str] = None
    tab_id: Optional[str] = None
    edit_action: str = ChangeActionEnum.ADD.value
    section_id: Optional[str] = None
    section_register_id: Optional[str] = None
    internal_record_id: Optional[str] = None
    change_payload: Optional[List[ChangePayload]] = None
    # Already-uploaded catalog documents with display labels
    documents: Optional[List[DocumentAttachment]] = None
    # For approve/reject operations
    change_request_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None


class ChangeRequestResponsePayload(RegisterPayload):
    """Response payload for change requests - returned to clients"""
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


#==============================================================================
# Intake Form Data
#==============================================================================

class IntakeFormData(BaseModel):
    """Intake form data."""
    submission_id: Optional[str] = None
    form_id: Optional[str] = None
    register_id: Optional[str] = None
    draft_status: Optional[str] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    finalized_at: Optional[str] = None
    first_created_at: Optional[str] = None
    submission_source: Optional[str] = None
    partner_id: Optional[str] = None
    register_ingest_process_status: Optional[str] = None
    register_ingest_processed_timestamp: Optional[str] = None
    register_ingest_process_attempts: Optional[int] = None
    register_ingest_process_last_error_code: Optional[str] = None
    number_of_verifications_required: Optional[int] = None
    number_of_verifications_done: Optional[int] = None
    created_by: Optional[str] = None
    last_updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SectionPayloadResponseItem(BaseModel):
    """A single section payload item returned by get_intake_form."""
    section_id: str
    section_register_id: str
    is_list: bool
    section_order: Optional[int] = None
    records: List[dict]
    documents: Optional[List[DocumentData]] = None

class SubmissionResponsePayload(IntakeFormData):
    """Submission response payload."""
    section_payloads: Optional[List[SectionPayloadResponseItem]] = None


class SectionPayloadInput(BaseModel):
    """A single section payload item for saving an intake form."""
    section_id: str
    intake_form_section_payload: List[dict]
    # Desired document set for the section (g2p_registry_documents).
    # None = no-op; [] = clear; list = full desired set (diff-synced by document_id).
    documents: Optional[List[DocumentAttachment]] = None


class SaveSubmissionDraftRequestPayload(BaseModel):
    """Request payload for save_submission_draft (create or update, always DRAFT)."""
    submission_id: Optional[str] = None
    form_id: str
    register_id: str
    submission_source: Optional[str] = None
    partner_id: Optional[str] = None
    section_payloads: Optional[List[SectionPayloadInput]] = None
    created_by: Optional[str] = None


class FinalizeSubmissionRequestPayload(BaseModel):
    """Request payload for finalize_submission (DRAFT -> FINAL)."""
    submission_id: str


class ApproveRejectSubmissionRequestPayload(BaseModel):
    """Request payload for approve_submission / reject_submission."""
    submission_id: str
    approved_by: Optional[str] = None


class GetSubmissionRequestPayload(BaseModel):
    """Get single submission request payload."""
    submission_id: str


class SearchInSubmissionRequestPayload(BaseModel):
    """Search in submission section payloads request payload."""
    register_id: Optional[str] = None
    form_id: Optional[str] = None


class GetChangeRequestsForSubmissionRequestPayload(BaseModel):
    """Get change requests for a submission."""
    submission_id: str


class GetNumberOfPendingChangeRequestsForSubmissionRequestPayload(BaseModel):
    """Get count of pending change requests for a submission."""
    submission_id: str


class NumberOfPendingChangeRequestsForSubmissionData(BaseModel):
    """Pending change request count for a submission."""
    number_of_pending_change_requests: int


class GetIntakeFormsForRegisterRequestPayload(BaseModel):
    register_id: str


class GetIntakeFormMetadataRequestPayload(BaseModel):
    register_id: str
    intake_form_id: str


class IntakeFormSubmissionsSummaryData(BaseModel):
    """Summary statistics for intake form submissions."""
    total_submissions: int
    total_draft_submissions: int
    total_final_submissions: int
    total_approval_pending_submissions: int
    total_ingested_submissions: int
    total_approved_submissions: int
    total_rejected_submissions: int


# =============================================================================
# Version and History Data
# =============================================================================

class NumberOfVersionsData(BaseModel):
    register_id: str
    internal_record_id: str
    tab_id: str
    number_of_versions: int
    last_updated_by: Optional[str] = None
    last_updated_at: Optional[datetime] = None
    last_approved_by: Optional[str] = None
    last_approved_at: Optional[datetime] = None


class RecordHistoryData(BaseModel):
    """
    History record data with flattened additional fields.
    Extra fields from the register history implementation table are included at root level.
    """
    model_config = ConfigDict(extra="allow", from_attributes=True)

    history_record_id: str
    internal_record_id: str
    change_request_id: str
    tab_id: str
    section_id: str
    is_primary_section: bool = False
    submission_id: Optional[str] = None
    change_request_source: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


class RecordHistoryListData(BaseModel):
    """Container for a list of history records with metadata"""
    register_id: str
    internal_record_id: str
    tab_id: str
    history_records: List["RecordHistoryData"] = []


class VersionDatesData(BaseModel):
    """Container for a list of unique version dates"""
    register_id: str
    internal_record_id: str
    tab_id: str
    version_dates: List[str] = []


class VersionForDateData(BaseModel):
    """Individual change record for a specific date"""
    change_request_id: str
    created_at: str
    request_id: Optional[str] = None


class VersionsForDateData(BaseModel):
    """Container for changes for a specific section and date"""
    register_id: str
    internal_record_id: str
    tab_id: str
    truncated_created_date: str
    section_id: str
    section_mnemonic: str
    changes: List[VersionForDateData] = []


# =============================================================================
# Pending Change Requests Data
# =============================================================================

class NumberOfPendingChangeRequestsData(BaseModel):
    subject_register_id: str
    subject_record_id: str
    tab_id: str
    number_of_pending_change_requests: int


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

    class Config:
        from_attributes: bool = True


class CrossRegisterChangesData(BaseModel):
    cross_register_changes: list["CrossRegisterChangeRequestData"]


class ChangeRequestData(BaseModel):
    change_request_id: str
    record_name: Optional[str] = None
    register_id: str
    tab_id: str
    internal_record_id: str
    section_id: str
    section_mnemonic: str
    is_list: bool = False
    is_primary_section: bool = False
    is_core_section: bool = False
    section_register_id: str
    source_partner_id: str
    created_by: str
    created_at: Optional[str] = None
    no_of_verifications_required: Optional[int] = None
    no_of_verifications_done: Optional[int] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    change_payload: Optional[dict | List[dict]] = None
    current_register_data: Optional[dict | List[dict]] = None

    class Config:
        from_attributes: bool = True


class ChangeRequestFlattenedData(BaseModel):
    """Change request data with flattened fields from change_payload"""
    change_request_id: str
    record_name: Optional[str] = None
    register_id: str
    tab_id: str
    internal_record_id: str
    section_id: str
    section_mnemonic: str
    is_primary_section: bool = False
    is_core_section: bool = False
    source_partner_id: str
    created_by: str
    created_at: Optional[str] = None
    no_of_verifications_required: Optional[int] = None
    no_of_verifications_done: Optional[int] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

    class Config:
        from_attributes: bool = True
        extra = "allow"  # Allow extra fields from flattened change_payload


class ChangeRequestsData(BaseModel):
    change_requests: List[ChangeRequestData]

    class Config:
        from_attributes: bool = True


# =============================================================================
# Verification Data
# =============================================================================

class VerificationData(BaseModel):
    verification_id: str
    register_id: str
    internal_record_id: Optional[str] = None
    section_id: Optional[str] = None
    change_request_id: Optional[str] = None
    submission_id: Optional[str] = None
    verified_by: str
    verified_at: Optional[str] = None
    verification_observations: Optional[str] = None
    is_approved: bool

    class Config:
        from_attributes: bool = True


class VerificationsData(BaseModel):
    verifications: List[VerificationData]

    class Config:
        from_attributes: bool = True


class AddVerificationPayload(BaseModel):
    submission_id: Optional[str] = None
    change_request_id: Optional[str] = None
    verification_observations: Optional[str] = None
    verified_by: Optional[str] = None
    is_approved: bool


# =============================================================================
# Deduplication Data
# =============================================================================

class DeduplicationRegisterResultData(BaseModel):
    """Deduplication result for a change request against a register record."""
    dedup_result_id: str
    change_request_id: str
    internal_record_id: str
    match_score: float
    field_matches: dict
    created_at: Optional[str] = None

    class Config:
        from_attributes: bool = True


class DeduplicationChangerequestResultData(BaseModel):
    """Deduplication result for a change request against another change request."""
    dedup_result_id: str
    change_request_id: str
    candidate_change_request_id: str
    match_score: float
    field_matches: dict
    created_at: Optional[str] = None

    class Config:
        from_attributes: bool = True


class DeduplicationRegisterResultsData(BaseModel):
    """List of deduplication results for a change request against register records."""
    results: List[DeduplicationRegisterResultData]

    class Config:
        from_attributes: bool = True


class DeduplicationChangerequestResultsData(BaseModel):
    """List of deduplication results for a change request against other change requests."""
    results: List[DeduplicationChangerequestResultData]

    class Config:
        from_attributes: bool = True


# =============================================================================
# Register Schema Data
# =============================================================================

class RegisterSchemaData(BaseModel):
    """Schema data for a register including deduplication, search result, and filter configurations."""
    register_id: str
    deduplicate_schema: Optional[List[dict]] = None
    search_result_schema: Optional[List[dict]] = None
    filter_schema: Optional[List[dict]] = None

    class Config:
        from_attributes: bool = True


class RegisterFieldMetadata(BaseModel):
    """One column mapped on the register SQLAlchemy ORM model (`G2PRegister*`)."""

    field_name: str
    data_type: str
    required: bool = False
    nullable: bool = True


class RegisterFieldsData(BaseModel):
    """All ORM columns for a register definition (model + mixin table mapping)."""

    register_id: str
    register_mnemonic: str
    fields: List[RegisterFieldMetadata]

    class Config:
        from_attributes: bool = True


class RegisterSectionData(BaseModel):
    """Section data for a register representing UI schema for a section."""
    section_register_id: str
    register_id: str
    section_id: str
    # tab_id: str
    # used_for_new_intake_form: bool = False
    # tab_label: Optional[str] = None
    # intake_form_name: Optional[str] = None
    # intake_form_description: Optional[str] = None
    section_mnemonic: str
    section_description: Optional[str] = None
    documents_required: bool = False
    no_of_verifications_required: int = 0
    auto_approval: bool = False
    cr_auto_approve_for_bene_portal: bool = False
    cr_auto_approve_for_agent_portal: bool = False
    cr_auto_approve_for_staff_portal: bool = False
    cr_auto_approve_for_partner: bool = False
    cr_auto_approve_for_intake_form: bool = False
    is_list: bool = False
    register_purpose: Optional[str] = None
    is_primary_section: bool = False
    is_core_section: Optional[bool] = False
    section_order: int = 0
    section_ui_schema: Optional[dict] = None
    register_relation: Optional[RegisterRelationEnum] = None
    section_weightage: Optional[float] = 0.0

    class Config:
        from_attributes: bool = True


class RegisterTabRecordData(BaseModel):
    """
    Records for a single section_register_id within a tab.
    Multiple sections with the same section_register_id are deduplicated.
    """
    section_register_id: str
    is_list: bool = False
    records: List[RecordData]



# =============================================================================
# Registry Configuration Schemas
# =============================================================================

class RegistryConfigurationData(BaseModel):
    """Data for registry configuration"""
    configuration_id: str
    registry_name: str
    registry_logo: Optional[str] = None  # BASE64 encoded image
    registry_favicon: Optional[str] = None  # BASE64 encoded square icon
    registry_theme_id: Optional[str] = None
    registry_language_id: Optional[str] = None

    class Config:
        from_attributes: bool = True


class RegistryConfigurationPayload(BaseModel):
    """Payload for creating registry configuration"""
    registry_name: str
    registry_logo: Optional[str] = None  # BASE64 encoded image
    registry_favicon: Optional[str] = None  # BASE64 encoded square icon
    registry_theme_id: Optional[str] = None
    registry_language_id: Optional[str] = None


class RegistryConfigurationUpdatePayload(BaseModel):
    """Payload for updating registry configuration"""
    configuration_id: str
    registry_name: Optional[str] = None
    registry_logo: Optional[str] = None  # BASE64 encoded image
    registry_favicon: Optional[str] = None  # BASE64 encoded square icon
    registry_theme_id: Optional[str] = None
    registry_language_id: Optional[str] = None


# =============================================================================
# Change Request Additional Schemas
# =============================================================================

class NumberOfRequestsPendingData(BaseModel):
    """Data for get_number_of_requests_pending endpoint"""
    number_of_requests_pending: int


class EarliestPendingChangeRequestData(BaseModel):
    """Data for get_earliest_pending_change_request endpoint"""
    change_request_id: Optional[str] = None
    record_name: Optional[str] = None
    register_id: Optional[str] = None
    tab_id: Optional[str] = None
    internal_record_id: Optional[str] = None
    section_id: Optional[str] = None
    source_partner_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    no_of_verifications_required: Optional[int] = None
    no_of_verifications_done: Optional[int] = None
    approval_status: Optional[str] = None
    change_payload: Optional[dict] = None

    class Config:
        from_attributes: bool = True


# =============================================================================
# Register Request Payloads
# =============================================================================

class EmptyRequestPayload(BaseModel):
    """Empty payload for requests that don't require any parameters"""
    pass


class ChildRegisterRequestPayload(BaseModel):
    register_id: str


class SearchRegisterRequestPayload(BaseModel):
    register_id: str


class SearchChangeRequestRequestPayload(BaseModel):
    pass


class GetChildRegistersRequestPayload(BaseModel):
    register_id: str


class GetMasterRegisterRequestPayload(BaseModel):
    register_id: str


class GetNumberOfVersionsRequestPayload(BaseModel):
    register_id: str
    internal_record_id: str
    tab_id: str


class GetRecordHistoryRequestPayload(BaseModel):
    register_id: str
    internal_record_id: str
    tab_id: str


class GetVersionDatesRequestPayload(BaseModel):
    register_id: str
    internal_record_id: str
    tab_id: str


class GetChangesForDateRequestPayload(BaseModel):
    register_id: str
    internal_record_id: str
    tab_id: str
    truncated_created_date: str


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


class GetSubjectRecordRequestPayload(BaseModel):
    subject_register_id: str
    subject_record_id: str


class GetVerificationsRequestPayload(BaseModel):
    change_request_id: Optional[str] = None
    submission_id: Optional[str] = None


class GetDeduplicationRegisterResultsRequestPayload(BaseModel):
    change_request_id: str


class GetDeduplicationChangerequestResultsRequestPayload(BaseModel):
    change_request_id: str


class GetRegisterSchemaRequestPayload(BaseModel):
    register_id: str


class GetRegisterFieldsRequestPayload(BaseModel):
    register_id: str


class GetRegisterSectionsRequestPayload(BaseModel):
    register_id: str


class GetRegisterTabSectionsRequestPayload(BaseModel):
    register_id: str
    tab_id: str


class GetRegisterTabsRequestPayload(BaseModel):
    register_id: str
    used_for_new_intake_form: Optional[bool] = None


class AddRegisterTabRequestPayload(BaseModel):
    register_id: str
    tab_label: str
    tab_order: int = 0
    used_for_new_intake_form: bool = False
    no_of_verifications_required: int = 0
    intake_form_name: Optional[str] = None
    intake_form_description: Optional[str] = None
    intake_form_auto_approve: bool = False
    is_active: bool = True


class DeleteRegisterTabRequestPayload(BaseModel):
    tab_id: str


class EditRegisterTabRequestPayload(BaseModel):
    tab_id: str
    tab_label: Optional[str] = None
    tab_order: Optional[int] = None
    used_for_new_intake_form: Optional[bool] = None
    no_of_verifications_required: Optional[int] = None
    intake_form_name: Optional[str] = None
    intake_form_description: Optional[str] = None
    intake_form_auto_approve: Optional[bool] = None
    is_active: Optional[bool] = None


class GetRegisterSectionRequestPayload(BaseModel):
    register_id: str
    section_id: str


class AddRegisterSectionRequestPayload(BaseModel):
    section_register_id: str
    register_id: str
    tab_id: str
    section_mnemonic: str
    section_description: Optional[str] = None
    documents_required: bool = False
    no_of_verifications_required: int = 0
    auto_approval: bool = False
    cr_auto_approve_for_bene_portal: bool = False
    cr_auto_approve_for_agent_portal: bool = False
    cr_auto_approve_for_staff_portal: bool = False
    cr_auto_approve_for_partner: bool = False
    cr_auto_approve_for_intake_form: bool = False
    is_list: bool = False
    is_primary_section: bool = False
    is_core_section: Optional[bool] = False
    section_ui_schema: Optional[dict] = None


class DeleteRegisterSectionRequestPayload(BaseModel):
    section_id: str


class GetRegisterSectionUISchemaRequestPayload(BaseModel):
    section_id: str


class RegisterSectionUISchemaData(BaseModel):
    """UI schema data for a register section."""
    section_id: str
    section_ui_schema: Optional[dict] = None


class UpdateRegisterSectionRequestPayload(BaseModel):
    """
    Only allows editing: section_mnemonic, section_description, no_of_verifications_required,
    documents_required, auto_approval, cr_auto_approve_for_*, is_primary_section
    """
    section_id: str
    section_mnemonic: Optional[str] = None
    section_description: Optional[str] = None
    no_of_verifications_required: Optional[int] = None
    documents_required: Optional[bool] = None
    auto_approval: Optional[bool] = None
    cr_auto_approve_for_bene_portal: Optional[bool] = None
    cr_auto_approve_for_agent_portal: Optional[bool] = None
    cr_auto_approve_for_staff_portal: Optional[bool] = None
    cr_auto_approve_for_partner: Optional[bool] = None
    cr_auto_approve_for_intake_form: Optional[bool] = None
    is_primary_section: Optional[bool] = None
    is_core_section: Optional[bool] = None
    section_weightage: Optional[float] = None


class UpdateRegisterSectionUISchemaRequestPayload(BaseModel):
    register_id: str
    section_id: str
    section_ui_schema: Optional[dict] = None


class CreateRegisterRequestPayload(BaseModel):
    register_mnemonic: str
    register_description: Optional[str] = None
    master_register_id: Optional[str] = None
    dedup_is_enabled: bool = False
    dedup_threshold_score: Optional[float] = None
    register_icon: Optional[str] = None
    register_rank: Optional[int] = None
    register_purpose: Optional[str] = None
    functional_id_generation_required: bool = False
    completion_score_required: bool = False
    outgest_applicable: bool = False
    requires_registrant_authentication: bool = False
    registrant_authentication_validity_days: Optional[int] = 730
    registrant_re_auth_warning_days_before: Optional[int] = 30


class EditRegisterRequestPayload(BaseModel):
    register_id: str
    register_mnemonic: Optional[str] = None
    register_description: Optional[str] = None
    master_register_id: Optional[str] = None
    dedup_is_enabled: Optional[bool] = None
    dedup_threshold_score: Optional[float] = None
    register_icon: Optional[str] = None
    register_rank: Optional[int] = None
    register_purpose: Optional[str] = None
    functional_id_generation_required: Optional[bool] = None
    completion_score_required: Optional[bool] = None
    outgest_applicable: Optional[bool] = None
    requires_registrant_authentication: Optional[bool] = None
    registrant_authentication_validity_days: Optional[int] = None
    registrant_re_auth_warning_days_before: Optional[int] = None


class DeleteRegisterRequestPayload(BaseModel):
    register_id: str


class UpdateRegisterSchemaRequestPayload(BaseModel):
    register_id: str
    deduplicate_schema: Optional[list[dict]] = None
    search_result_schema: Optional[list[dict]] = None
    filter_schema: Optional[list[dict]] = None


class UpdateDedupIsEnabledRequestPayload(BaseModel):
    register_id: str
    dedup_is_enabled: bool


class UpdateDedupThresholdScoreRequestPayload(BaseModel):
    register_id: str
    dedup_threshold_score: float


class UpdateDeduplicationSchemaRequestPayload(BaseModel):
    register_id: str
    deduplicate_schema: list[dict]


class UpdateSearchResultSchemaRequestPayload(BaseModel):
    register_id: str
    search_result_schema: list[dict]


class GetSectionRecordsRequestPayload(BaseModel):
    subject_register_id: str
    subject_record_id: str
    section_register_id: str


class GetRegisterTabRecordsRequestPayload(BaseModel):
    subject_register_id: str
    subject_record_id: str
    tab_id: str


class CreateRegistryConfigurationRequestPayload(BaseModel):
    registry_name: str
    registry_logo: Optional[str] = None  # BASE64 encoded image
    registry_favicon: Optional[str] = None  # BASE64 encoded square icon
    registry_theme_id: Optional[str] = None
    registry_language_id: Optional[str] = None


class UpdateRegistryConfigurationRequestPayload(BaseModel):
    configuration_id: str
    registry_name: Optional[str] = None
    registry_logo: Optional[str] = None  # BASE64 encoded image
    registry_favicon: Optional[str] = None  # BASE64 encoded square icon
    registry_theme_id: Optional[str] = None
    registry_language_id: Optional[str] = None


class RegistryThemeData(BaseModel):
    theme_id: str
    theme_mnemonic: str
    is_factory_shipped: bool

    class Config:
        from_attributes: bool = True


class RegistryThemeValueData(BaseModel):
    theme_value_id: str
    theme_id: str
    attribute_name: str
    attribute_value: str

    class Config:
        from_attributes: bool = True


class CreateThemeRequestPayload(BaseModel):
    theme_mnemonic: str
    theme_values: list["ThemeAttributeValueInput"]


class RemoveThemeRequestPayload(BaseModel):
    theme_id: str


class UpdateThemeValuesRequestPayload(BaseModel):
    theme_id: str
    theme_attribute_values: list["ThemeAttributeValueInput"]


class GetThemeValuesRequestPayload(BaseModel):
    theme_id: str


class ThemeAttributeValueInput(BaseModel):
    attribute_name: str
    attribute_value: str


class ThemeOperationData(BaseModel):
    theme_id: str
    success: bool = True


# =============================================================================
# Registry Languages Schemas
# =============================================================================

class RegistryLanguageData(BaseModel):
    language_id: str
    language_code: str
    language_label: str
    language_flag_base64: Optional[str] = None
    is_default: bool = False
    core_translation: Optional[dict] = None
    domain_translation: Optional[dict] = None

    class Config:
        from_attributes: bool = True

class GetLanguageRequestPayload(BaseModel):
    language_id: str


class CreateLanguageRequestPayload(BaseModel):
    language_code: str
    language_label: str
    language_flag_base64: Optional[str] = None
    is_default: bool = False
    core_translation: Optional[dict] = None
    domain_translation: Optional[dict] = None


class UpdateLanguageRequestPayload(BaseModel):
    language_id: str
    language_code: Optional[str] = None
    language_label: Optional[str] = None
    language_flag_base64: Optional[str] = None
    is_default: Optional[bool] = None
    core_translation: Optional[dict] = None
    domain_translation: Optional[dict] = None


class RemoveLanguageRequestPayload(BaseModel):
    language_id: str


class LanguageOperationData(BaseModel):
    language_id: str
    success: bool = True


# =============================================================================
# Attribute Schemas
# =============================================================================

class AttributeData(BaseModel):
    attribute_id: str
    attribute_code: str
    attribute_display: str
    is_hierarchical: bool


class AttributeValueData(BaseModel):
    value_id: str
    attribute_id: str
    value_code: str
    value_display: str
    parent_value_id: Optional[str] = None
    sort_order: int


class GetAttributesRequestPayload(BaseModel):
    pass


class GetAttributeRequestPayload(BaseModel):
    attribute_id: str


class CreateAttributeRequestPayload(BaseModel):
    attribute_code: str
    attribute_display: str
    is_hierarchical: bool = False


class UpdateAttributeRequestPayload(BaseModel):
    attribute_id: str
    attribute_code: Optional[str] = None
    attribute_display: Optional[str] = None
    is_hierarchical: Optional[bool] = None


class DeleteAttributeRequestPayload(BaseModel):
    attribute_id: str


class GetAttributeValuesRequestPayload(BaseModel):
    attribute_id: Optional[str] = None
    parent_value_id: Optional[str] = None


class GeoLevelValueData(BaseModel):
    level_value_id: str
    level_value_mnemonic: str
    level_value_display: Optional[str] = None
    parent_level_value_id: Optional[str] = None
    level_mnemonic: Optional[str] = None


class CreateAttributeValueRequestPayload(BaseModel):
    attribute_id: str
    value_code: str
    value_display: str
    parent_value_id: Optional[str] = None
    sort_order: int = 0


class UpdateAttributeValueRequestPayload(BaseModel):
    value_id: str
    value_code: Optional[str] = None
    value_display: Optional[str] = None
    parent_value_id: Optional[str] = None
    sort_order: Optional[int] = None


class DeleteAttributeValueRequestPayload(BaseModel):
    value_id: str


class CreateAttributeResponsePayload(BaseModel):
    attribute: AttributeData


class UpdateAttributeResponsePayload(BaseModel):
    attribute: AttributeData


class DeleteAttributeResponsePayload(BaseModel):
    attribute_id: str


class CreateAttributeValueResponsePayload(BaseModel):
    attribute_value: AttributeValueData


class UpdateAttributeValueResponsePayload(BaseModel):
    attribute_value: AttributeValueData


class DeleteAttributeValueResponsePayload(BaseModel):
    value_id: str


# =============================================================================
# Allowed Parents For Child Section Schemas
# =============================================================================

class GetAllowedParentsForChildSectionRequestPayload(BaseModel):
    subject_register_id: str
    internal_record_id: str
    section_register_id: str


class AllowedParentRecordData(BaseModel):
    internal_record_id: str
    record_name: Optional[str] = None


class AllowedParentsData(BaseModel):
    register_mnemonic: str
    master_register_id: Optional[str] = None
    allowed_parents: List[AllowedParentRecordData]