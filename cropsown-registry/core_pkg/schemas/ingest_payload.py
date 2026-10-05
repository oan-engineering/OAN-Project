from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from ..models import InputMechanismTypeEnum


# =============================================================================
# Ingest Data Schemas (response payloads)
# =============================================================================

class IngestionSummaryData(BaseModel):
    no_of_messages: int
    no_of_partners: int
    no_of_data_models: int


class IngestionDataSearchResultData(BaseModel):
    ingest_id: str
    partner_id: str
    partner_mnemonic: str
    data_model_id: str
    data_model_mnemonic: str
    ingest_message_id: str
    ingest_correlation_id: str
    receipt_date_time: datetime
    classification_status: str
    classification_date_time: Optional[datetime] = None
    classification_number_of_attempts: Optional[int] = None
    classification_latest_error_code: Optional[str] = None

    intake_form_id: Optional[str] = None
    intake_form_mnemonic: Optional[str] = None
    intake_form_submission_id: Optional[str] = None
    register_id: Optional[str] = None
    register_mnemonic: Optional[str] = None
    semantic_pattern_id: Optional[str] = None

    pipeline_action: Optional[str] = None
    section_id: Optional[str] = None
    section_mnemonic: Optional[str] = None
    internal_record_id: Optional[str] = None
    change_request_id: Optional[str] = None

    template_id: Optional[str] = None
    template_document_id: Optional[str] = None
    transformation_status: Optional[str] = None
    transformation_date_time: Optional[datetime] = None
    transformation_number_of_attempts: Optional[int] = None
    transformation_latest_error_code: Optional[str] = None
    ingestion_status: Optional[str] = None
    ingestion_date_time: Optional[datetime] = None
    ingestion_number_of_attempts: Optional[int] = None
    ingestion_latest_error_code: Optional[str] = None


class IngestionDataPayload(BaseModel):
    raw_data_json: Optional[dict] = None
    enriched_data_json: Optional[dict] = None
    transformed_data_json: Optional[dict] = None


class IngestDataPayload(BaseModel):
    correlation_id: str


# =============================================================================
# IncomingPartner Schemas
# =============================================================================

class IncomingPartnerPayload(BaseModel):
    partner_id: Optional[str] = None
    partner_mnemonic: str
    keymanager_reference_id: str
    is_active: bool = True

    class Config:
        from_attributes: bool = True


class IncomingPartnerUpdatePayload(BaseModel):
    """Update payload for IncomingPartner - only allows updating specific fields"""
    partner_mnemonic: Optional[str] = None
    keymanager_reference_id: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes: bool = True


class IncomingPartnerData(BaseModel):
    partner_id: str
    partner_mnemonic: str
    keymanager_reference_id: str
    is_active: bool

    class Config:
        from_attributes: bool = True


# =============================================================================
# IncomingModelKeyPath Schemas
# =============================================================================

class IncomingModelKeyPathPayload(BaseModel):
    key_path_id: Optional[str] = None
    key_path_for_message_id: str
    data_model_id: str
    key_path_for_sender: str
    key_path_for_signature: str
    key_path_for_signature_payload: str
    is_list: bool = False
    key_path_for_list_elements: Optional[str] = None

    class Config:
        from_attributes: bool = True


class IncomingModelKeyPathUpdatePayload(BaseModel):
    """Update payload for IncomingModelKeyPath - only allows updating specific fields"""
    key_path_id: str
    key_path_for_message_id: Optional[str] = None
    key_path_for_sender: Optional[str] = None
    key_path_for_signature: Optional[str] = None
    key_path_for_signature_payload: Optional[str] = None
    is_list: Optional[bool] = None
    key_path_for_list_elements: Optional[str] = None

    class Config:
        from_attributes: bool = True


class GetIncomingKeyPathPayload(BaseModel):
    """Get payload for IncomingModelKeyPath"""
    key_path_id: str

    class Config:
        from_attributes: bool = True


class IncomingModelKeyPathData(BaseModel):
    key_path_id: str
    data_model_id: str
    key_path_for_message_id: str
    key_path_for_sender: str
    key_path_for_signature: str
    key_path_for_signature_payload: str
    is_list: bool
    key_path_for_list_elements: Optional[str]

    class Config:
        from_attributes: bool = True


class IncomingModelKeyPathListData(BaseModel):
    """Data for list API - includes data_model_mnemonic"""
    key_path_id: str
    data_model_id: str
    data_model_mnemonic: str
    is_list: bool

    class Config:
        from_attributes: bool = True


# =============================================================================
# IncomingModelSemanticPattern Schemas
# =============================================================================

class IncomingModelSemanticPatternPayload(BaseModel):
    data_model_id: str
    register_id: str
    intake_form_id: str
    section_id: Optional[str] = None
    pattern_for_register: Optional[str] = None
    pattern_for_intake_form: str
    pattern_for_section: Optional[str] = None
    key_path_for_business_payload: str
    raw_payload_enricher_class: Optional[str] = None

    class Config:
        from_attributes: bool = True


class IncomingModelSemanticPatternUpdatePayload(BaseModel):
    """Update payload for IncomingModelSemanticPattern - only allows updating specific fields"""

    semantic_pattern_id: str
    section_id: Optional[str] = None
    pattern_for_register: Optional[str] = None
    pattern_for_intake_form: Optional[str] = None
    pattern_for_section: Optional[str] = None
    key_path_for_business_payload: Optional[str] = None
    raw_payload_enricher_class: Optional[str] = None

    class Config:
        from_attributes: bool = True


class GetIncomingSemanticPatternPayload(BaseModel):
    """Get/Delete payload for IncomingModelSemanticPattern"""
    semantic_pattern_id: str

    class Config:
        from_attributes: bool = True


class IncomingModelSemanticPatternData(BaseModel):
    semantic_pattern_id: str
    data_model_id: str
    data_model_mnemonic: Optional[str] = None
    register_id: str
    register_mnemonic: Optional[str] = None
    intake_form_id: str
    intake_form_mnemonic: Optional[str] = None
    section_id: Optional[str] = None
    section_mnemonic: Optional[str] = None
    pattern_for_register: Optional[str] = None
    pattern_for_intake_form: str
    pattern_for_section: Optional[str] = None
    key_path_for_business_payload: str
    raw_payload_enricher_class: Optional[str] = None

    class Config:
        from_attributes: bool = True


# =============================================================================
# IncomingModelRegisterSemanticPattern Schemas
# =============================================================================


class IncomingModelRegisterSemanticPatternPayload(BaseModel):
    data_model_id: str
    register_id: str
    pattern_for_register: str
    key_path_for_record_identifier: str

    class Config:
        from_attributes: bool = True


class IncomingModelRegisterSemanticPatternUpdatePayload(BaseModel):
    register_semantic_pattern_id: str
    pattern_for_register: Optional[str] = None
    key_path_for_record_identifier: Optional[str] = None

    class Config:
        from_attributes: bool = True


class GetIncomingRegisterSemanticPatternPayload(BaseModel):
    register_semantic_pattern_id: str

    class Config:
        from_attributes: bool = True


class IncomingModelRegisterSemanticPatternData(BaseModel):
    register_semantic_pattern_id: str
    data_model_id: str
    data_model_mnemonic: Optional[str] = None
    register_id: str
    register_mnemonic: Optional[str] = None
    pattern_for_register: str
    key_path_for_record_identifier: str

    class Config:
        from_attributes: bool = True


# =============================================================================
# IncomingTemplate Schemas
# =============================================================================

class IncomingTemplatePayload(BaseModel):
    register_id: str
    data_model_id: str
    template_document_id: str
    jsonld_expansion_required: bool = False

    class Config:
        from_attributes: bool = True


class IncomingTemplateUpdatePayload(BaseModel):
    """Update payload for IncomingTemplate - only allows updating specific fields."""
    template_id: str
    template_document_id: Optional[str] = None
    jsonld_expansion_required: Optional[bool] = None

    class Config:
        from_attributes: bool = True


class GetIncomingTemplatePayload(BaseModel):
    """Get/Delete payload for IncomingTemplate."""
    template_id: str

    class Config:
        from_attributes: bool = True


class IncomingTemplateData(BaseModel):
    template_id: str
    register_id: str
    register_mnemonic: Optional[str] = None
    data_model_id: str
    data_model_mnemonic: Optional[str] = None
    template_document_id: str
    jsonld_expansion_required: bool

    class Config:
        from_attributes: bool = True


# =============================================================================
# DataModel Schemas
# =============================================================================

class DataModelPayload(BaseModel):
    data_model_id: Optional[str] = None
    data_model_mnemonic: str
    pattern_for_data_model: str
    response_template_document_id: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes: bool = True


class DataModelUpdatePayload(BaseModel):
    """Update payload for DataModel - only allows updating specific fields"""
    data_model_id: str
    data_model_mnemonic: Optional[str] = None
    pattern_for_data_model: Optional[str] = None
    response_template_document_id: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes: bool = True


class DataModelIdPayload(BaseModel):
    data_model_id: str

    class Config:
        from_attributes: bool = True


class DataModelData(BaseModel):
    data_model_id: str
    data_model_mnemonic: str
    pattern_for_data_model: str
    response_template_document_id: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes: bool = True


class ChangeResponseTemplateFilePayload(BaseModel):
    """Payload for changing response template file of a DataModel"""
    data_model_id: str

    class Config:
        from_attributes: bool = True


class ChangeActiveStatusPayload(BaseModel):
    """Payload for changing active status of a DataModel"""
    data_model_id: str
    is_active: bool

    class Config:
        from_attributes: bool = True


# =============================================================================
# SubscriptionActivityLog Schemas
# =============================================================================

class SubscriptionActivityLogPayload(BaseModel):
    is_unsubscribe: bool = False
    description: Optional[str] = None
    partner_id: str
    subscription_url: str
    registry_callback_url: str
    header: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes: bool = True


class SubscriptionActivityLogData(BaseModel):
    subscription_activity_log_id: str
    is_unsubscribe: bool
    description: Optional[str] = None
    partner_id: str
    subscription_url: str
    registry_callback_url: str
    header: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    date_time: datetime

    class Config:
        from_attributes: bool = True


# =============================================================================
# Ingestion Request Payloads
# =============================================================================

class EmptyIngestionRequestPayload(BaseModel):
    """Empty payload for requests that don't require any parameters"""
    pass


class GetIngestionDataRequestPayload(BaseModel):
    ingest_id: str

# =============================================================================
# G2P Input Mechanism Schemas
# =============================================================================

class G2PInputMechanismPayload(BaseModel):
    register_id: str

    class Config:
        from_attributes: bool = True


class G2PInputMechanismData(BaseModel):
    mechanism_id: str
    register_id: str
    mechanism_type: InputMechanismTypeEnum
    display_key: str

    class Config:
        from_attributes: bool = True
