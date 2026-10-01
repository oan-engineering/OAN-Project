import uuid
from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel
from datetime import datetime, timezone

class IncomingPartner(BaseORMModel):

    __tablename__ = "g2p_partners"

    partner_id: Mapped[str] = mapped_column(String, primary_key=True)
    partner_mnemonic: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    keymanager_reference_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class IncomingModelKeyPath(BaseORMModel):

    __tablename__ = "incoming_model_key_paths"

    key_path_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    key_path_for_message_id: Mapped[str] = mapped_column(String, nullable=False)
    key_path_for_sender: Mapped[str] = mapped_column(String, nullable=False)
    key_path_for_signature: Mapped[str] = mapped_column(String, nullable=False)
    key_path_for_signature_payload: Mapped[str] = mapped_column(String, nullable=False)
    is_list: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    key_path_for_list_elements: Mapped[str] = mapped_column(String, nullable=False)


class IncomingModelRegisterSemanticPattern(BaseORMModel):
    """First-pass resolver: target register + record identifier extraction for dynamic ADD/UPDATE."""

    __tablename__ = "incoming_model_register_semantic_patterns"

    register_semantic_pattern_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    pattern_for_register: Mapped[str] = mapped_column(String, nullable=False)
    key_path_for_record_identifier: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (Index("ix_incoming_model_register_semantic_data_model", "data_model_id"),)


class IncomingModelSemanticPattern(BaseORMModel):

    __tablename__ = "incoming_model_semantic_patterns"

    semantic_pattern_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False)
    intake_form_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    section_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    pattern_for_register: Mapped[str | None] = mapped_column(String, nullable=True)
    pattern_for_intake_form: Mapped[str] = mapped_column(String, nullable=True)
    pattern_for_section: Mapped[str | None] = mapped_column(String, nullable=True)
    key_path_for_business_payload: Mapped[str] = mapped_column(String, nullable=False)
    raw_payload_enricher_class: Mapped[str] = mapped_column(String, nullable=False)

class IncomingTemplate(BaseORMModel):

    __tablename__ = "incoming_templates"

    template_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # document_id of the template in g2p_registry_documents (TEMPLATES bucket)
    template_document_id: Mapped[str] = mapped_column(String, nullable=False)
    jsonld_expansion_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('data_model_id', 'register_id', name='uix_dro_2'),
    )

class SubscriptionActivityLog(BaseORMModel):

    __tablename__ = "subscription_activity_logs"

    subscription_activity_log_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    is_unsubscribe: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    partner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subscription_url: Mapped[str] = mapped_column(String, nullable=False)
    registry_callback_url: Mapped[str] = mapped_column(String, nullable=False)
    header: Mapped[JSON] = mapped_column(JSON, nullable=True)
    payload: Mapped[JSON] = mapped_column(JSON, nullable=True)
    response: Mapped[JSON] = mapped_column(JSON, nullable=True)
    date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
