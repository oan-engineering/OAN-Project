import enum
import uuid

from sqlalchemy import Boolean, DateTime, String, Text, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel

from .enum import MaritalStatusEnum, GenderEnum, RecordStatusEnum, ShapeTypeEnum, ChangeRequestSourceEnum


class G2PTableHistory(BaseORMModel):
    __abstract__ = True

    history_record_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    link_internal_record_id: Mapped[str] = mapped_column(String, nullable=True, index=True) # Link to internal_record_id of the parent

class G2PProgramRegisterHistory(BaseORMModel):
    __abstract__ = True

    history_record_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    foundational_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    link_foundational_id: Mapped[str] = mapped_column(String, nullable=True, index=True)


class G2PRegisterHistory(BaseORMModel):
    __abstract__ = True

    history_record_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    tab_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    change_request_id: Mapped[str] = mapped_column(String, nullable=True, index=False)
    submission_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    change_request_source: Mapped[ChangeRequestSourceEnum] = mapped_column(String, nullable=False)
    is_primary_section: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # This will come from change payload 
    functional_record_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    link_internal_record_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    link_foundational_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    record_name: Mapped[str] = mapped_column(String, nullable=True)
    record_image_document_id: Mapped[str] = mapped_column(Text, nullable=True)

    record_status: Mapped[RecordStatusEnum] = mapped_column(String, nullable=False, default=RecordStatusEnum.ACTIVE.value)
    record_status_reason: Mapped[str] = mapped_column(String, nullable=True)

    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    approved_by: Mapped[str] = mapped_column(String, nullable=False)
    approved_at: Mapped[str] = mapped_column(DateTime, nullable=False)


class G2PPersonHistory(BaseORMModel):
    __abstract__ = True

    foundational_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    middle_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    given_name: Mapped[str] = mapped_column(String, nullable=True)
    prefix: Mapped[str] = mapped_column(String, nullable=True)
    suffix: Mapped[str] = mapped_column(String, nullable=True)
    gender: Mapped[GenderEnum] = mapped_column(String, nullable=True)
    birth_date: Mapped[str] = mapped_column(Date, nullable=True)
    phone_numbers: Mapped[list] = mapped_column(JSONB, nullable=True)
    emails: Mapped[list] = mapped_column(JSONB, nullable=True)
    marital_status: Mapped[MaritalStatusEnum] = mapped_column(String, nullable=True)
    occupation: Mapped[str] = mapped_column(String, nullable=True)
    income_level: Mapped[str] = mapped_column(String, nullable=True)
    language_code: Mapped[str] = mapped_column(String, nullable=True)
    education_level: Mapped[str] = mapped_column(String, nullable=True)
    registration_date: Mapped[str] = mapped_column(Date, nullable=True)


class G2PGeoHistory(BaseORMModel):
    __abstract__ = True

    latitude: Mapped[str] = mapped_column(String, nullable=True)
    longitude: Mapped[str] = mapped_column(String, nullable=True)
    altitude: Mapped[str] = mapped_column(String, nullable=True)
    plus_code: Mapped[str] = mapped_column(String, nullable=True)
    address_line_1: Mapped[str] = mapped_column(String, nullable=True)
    address_line_2: Mapped[str] = mapped_column(String, nullable=True)
    postal_code: Mapped[str] = mapped_column(String, nullable=True)
    country_code: Mapped[str] = mapped_column(String, nullable=True)
    geo_lowest_level_value_id: Mapped[str] = mapped_column(String, nullable=True)
    geo_code_hierarchy_json: Mapped[str] = mapped_column(JSONB, nullable=True)


class G2PGeoShapeHistory(BaseORMModel):
    __abstract__ = True

    shape_type: Mapped[ShapeTypeEnum] = mapped_column(String, nullable=True)
    shape_coordinates_json: Mapped[str] = mapped_column(JSONB, nullable=True)

class G2PRegisterDocumentHistory(BaseORMModel):
    """Audit trail of documents promoted to live register sections (references g2p_registry_documents)."""
    __tablename__ = "g2p_register_document_history"

    document_history_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    # Origin of the promotion: change request approval or intake form ingestion
    change_request_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    submission_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    change_request_source: Mapped[ChangeRequestSourceEnum] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    approved_by: Mapped[str] = mapped_column(String, nullable=False)
    approved_at: Mapped[str] = mapped_column(DateTime, nullable=False)
