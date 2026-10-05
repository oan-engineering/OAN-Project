from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# Outgestion Data Schemas (response payloads)
# =============================================================================

class OutgestionSummaryData(BaseModel):
    no_of_messages: int
    no_of_topics: int
    no_of_data_models: int


class OutgestionDataSearchResultData(BaseModel):
    outgest_id: str
    payload_id: str
    change_request_id: Optional[str] = None
    intake_form_submission_id: Optional[str] = None
    internal_record_id: str
    register_id: str
    register_mnemonic: Optional[str] = None
    data_model_id: str
    data_model_mnemonic: Optional[str] = None
    topic_id: str
    websub_topic: Optional[str] = None
    created_at: datetime
    changed_by: str
    changed_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    changed_by_partner_id: Optional[str] = None
    partner_mnemonic: Optional[str] = None
    transformation_status: str
    transformation_datetime: Optional[datetime] = None
    transformation_number_of_attempts: Optional[int] = None
    transformation_latest_error_code: Optional[str] = None
    publish_status: Optional[str] = None
    publish_datetime: Optional[datetime] = None
    publish_number_of_attempts: Optional[int] = None
    publish_latest_error_code: Optional[str] = None


# =============================================================================
# Outgest Configuration Data Schemas (response payloads)
# =============================================================================

class OutgoingTopicData(BaseModel):
    topic_id: str
    register_id: str
    register_mnemonic: Optional[str] = None
    data_model_id: str
    data_model_mnemonic: Optional[str] = None
    websub_topic: str
    description: Optional[str] = None
    is_active: bool
    websub_register_status: str
    websub_register_datetime: Optional[datetime] = None
    websub_register_number_of_attempts: int
    websub_register_latest_error_message: Optional[str] = Field(
        default=None, validation_alias="websub_register_latest_error_code"
    )

    class Config:
        from_attributes = True


class OutgoingTemplateData(BaseModel):
    template_id: str
    register_id: str
    register_mnemonic: Optional[str] = None
    data_model_id: str
    data_model_mnemonic: Optional[str] = None
    template_document_id: str

    class Config:
        from_attributes = True


# =============================================================================
# Outgest Request Payload Schemas
# =============================================================================

class OutgoingTopicPayload(BaseModel):
    topic_id: Optional[str] = None
    register_id: str
    data_model_id: str
    websub_topic: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class GetOutgoingTopicPayload(BaseModel):
    topic_id: str

    class Config:
        from_attributes = True


class OutgoingTopicUpdatePayload(BaseModel):
    topic_id: str
    register_id: Optional[str] = None
    data_model_id: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class OutgoingTemplatePayload(BaseModel):
    register_id: str
    data_model_id: str
    template_document_id: str

    class Config:
        from_attributes = True


class OutgoingTemplateUpdatePayload(BaseModel):
    template_id: str
    template_document_id: Optional[str] = None

    class Config:
        from_attributes = True


class GetOutgoingTemplatePayload(BaseModel):
    template_id: str

    class Config:
        from_attributes = True


class EmptyOutgestionRequestPayload(BaseModel):
    pass


class GetOutgestionDataRequestPayload(BaseModel):
    outgest_id: str
