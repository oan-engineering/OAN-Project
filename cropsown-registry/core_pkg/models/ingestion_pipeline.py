import json

from sqlalchemy import Boolean, DateTime, Integer, String, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, validates
from openg2p_fastapi_common.models import BaseORMModel

from .data_models import ProcessStatusEnum
from .enum import PipelineActionEnum

class IncomingRawData(BaseORMModel):

    __tablename__ = "incoming_raw_data"

    ingest_id: Mapped[str] = mapped_column(String, primary_key=True)
    partner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ingest_message_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ingest_correlation_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    receipt_date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    classification_status: Mapped[str] = mapped_column(String, nullable=False, index=True, default=ProcessStatusEnum.PENDING.value)
    classification_date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    classification_number_of_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classification_latest_error_code: Mapped[str] = mapped_column(String, nullable=True)

class IncomingRawDataPayload(BaseORMModel):

    __tablename__ = "incoming_raw_data_payloads"

    ingest_id: Mapped[str] = mapped_column(String, nullable=False, index=True, primary_key=True)
    raw_data_json: Mapped[JSON] = mapped_column(JSON, nullable=True)
    raw_data_xml: Mapped[Text] = mapped_column(Text, nullable=True)
    raw_data_text: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index('ix_incoming_raw_data_payloads_raw_data_text_gin', 'raw_data_text', postgresql_using='gin', postgresql_ops={'raw_data_text': 'gin_trgm_ops'}),
    )

    @validates('raw_data_json')
    def update_raw_data_text(self, key, value):
        """Automatically populate search_text from change_payload JSON (array of payloads)"""
        if value:
            # Convert JSON to string representation for searching
            if isinstance(value, (dict, list)):
                self.raw_data_text = json.dumps(value)
            else:
                self.raw_data_text = str(value)
        return value


class IncomingEnrichedTransformedData(BaseORMModel):
    __tablename__ = "incoming_enriched_transformed_data"

    ingest_id: Mapped[str] = mapped_column(String, nullable=False, index=True, primary_key=True)
    enriched_data_json: Mapped[JSON] = mapped_column(JSON, nullable=True)
    enriched_data_xml: Mapped[Text] = mapped_column(Text, nullable=True)
    transformed_data_json: Mapped[JSON] = mapped_column(JSON, nullable=True)
    transformed_data_xml: Mapped[Text] = mapped_column(Text, nullable=True)

class IncomingClassifiedData(BaseORMModel):

    __tablename__ = "incoming_classified_data"

    ingest_id: Mapped[str] = mapped_column(String, nullable=False, index=True, primary_key=True)
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    partner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    pipeline_action: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
        default=PipelineActionEnum.ADD.value,
    )
    section_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    internal_record_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    change_request_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    intake_form_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    semantic_pattern_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    classified_date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    transformation_status: Mapped[str] = mapped_column(String, nullable=False, index=True, default=ProcessStatusEnum.PENDING.value)
    transformation_date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    transformation_number_of_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transformation_latest_error_code: Mapped[str] = mapped_column(String, nullable=True)
    ingestion_status: Mapped[str] = mapped_column(String, nullable=False, index=True, default=ProcessStatusEnum.NOT_APPLICABLE.value)
    ingestion_date_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    ingestion_number_of_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingestion_latest_error_code: Mapped[str] = mapped_column(String, nullable=True)

    intake_form_submission_id: Mapped[str] = mapped_column(String, nullable=True, index=True)