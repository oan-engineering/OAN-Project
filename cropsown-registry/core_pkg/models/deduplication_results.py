import uuid
from datetime import datetime

from sqlalchemy import String, Float, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class DeduplicationRegisterResult(BaseORMModel):
    """
    Stores deduplication results when comparing a change request against existing register records.
    """
    __tablename__ = "deduplication_register_results"

    dedup_result_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    change_request_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    field_matches: Mapped[JSON] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_dedup_register_change_request_id', 'change_request_id'),
        Index('idx_dedup_register_internal_record_id', 'internal_record_id'),
    )


class DeduplicationChangerequestResult(BaseORMModel):
    """
    Stores deduplication results when comparing a change request against other pending change requests.
    """
    __tablename__ = "deduplication_change_request_results"

    dedup_result_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    change_request_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    candidate_change_request_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    field_matches: Mapped[JSON] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_dedup_change_request_change_request_id', 'change_request_id'),
        Index('idx_dedup_change_request_candidate_change_request_id', 'candidate_change_request_id'),
    )


class DeduplicationIntakeFormRegisterResult(BaseORMModel):
    """
    Stores deduplication results when comparing an intake form submission against existing register records.
    """
    __tablename__ = "dedup_results_intake_forms_vs_register"

    dedup_result_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    field_matches: Mapped[JSON] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_dedup_if_register_submission_id', 'submission_id'),
        Index('idx_dedup_if_register_internal_record_id', 'internal_record_id'),
    )


class DeduplicationIntakeFormIntakeFormResult(BaseORMModel):
    """
    Stores deduplication results when comparing an intake form submission against other intake form submissions.
    """
    __tablename__ = "dedup_results_intake_forms_vs_intake_forms"

    dedup_result_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    candidate_submission_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    field_matches: Mapped[JSON] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_dedup_if_if_submission_id', 'submission_id'),
        Index('idx_dedup_if_if_candidate_submission_id', 'candidate_submission_id'),
    )

