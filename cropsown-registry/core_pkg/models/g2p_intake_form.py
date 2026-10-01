import uuid

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy.dialects.postgresql import UUID

from .enum import ApprovalStatusEnum, ChangeRequestSourceEnum, DeduplicationStatusEnum, IntakeFormStatusEnum, ProcessStatusEnum


def _default_application_reference() -> str:
    from ..helpers.application_reference_generator import generate_application_reference

    return generate_application_reference()


class G2PIntakeForm(BaseORMModel):
    __abstract__ = True

    submission_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_reference: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    async def get_link_internal_record_id(self, session=None):
        pass

class G2PIntakeFormSubmission(BaseORMModel):
    __tablename__ = "g2p_intake_form_submissions"

    submission_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_reference: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        index=True,
        default=_default_application_reference,
    )
    form_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    draft_status: Mapped[IntakeFormStatusEnum] = mapped_column(
        String,
        nullable=False,
        default=IntakeFormStatusEnum.DRAFT.value,
    )
    approval_status: Mapped[ApprovalStatusEnum] = mapped_column(
        String,
        nullable=False,
        default=ApprovalStatusEnum.PENDING.value,
    )
    approved_by: Mapped[str] = mapped_column(String, nullable=True)
    approved_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    remarks: Mapped[str] = mapped_column(Text, nullable=True)
    finalized_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    first_created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    last_updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    created_by: Mapped[str] = mapped_column(String, nullable=False)
    submission_source: Mapped[ChangeRequestSourceEnum] = mapped_column(String, nullable=False)
    partner_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    register_ingest_process_status: Mapped[ProcessStatusEnum] = mapped_column(
        String,
        nullable=False,
        default=ProcessStatusEnum.NOT_APPLICABLE.value,
    )
    register_ingest_processed_timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    register_ingest_process_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    register_ingest_process_last_error_code: Mapped[str] = mapped_column(Text, nullable=True)
    number_of_verifications_required: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    number_of_verifications_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    deduplication_status_vs_intake_forms: Mapped[str] = mapped_column(
        String, nullable=False, default=DeduplicationStatusEnum.PENDING.value, index=True
    )
    deduplication_intake_forms_process_timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    deduplication_intake_forms_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deduplication_intake_forms_error: Mapped[str] = mapped_column(Text, nullable=True)

    deduplication_status_vs_register: Mapped[str] = mapped_column(
        String, nullable=False, default=DeduplicationStatusEnum.PENDING.value, index=True
    )
    deduplication_register_process_timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    deduplication_register_forms_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deduplication_register_error: Mapped[str] = mapped_column(Text, nullable=True)

    awe_request_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    awe_request_status_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


G2PIntakeFormSubmissions = G2PIntakeFormSubmission


class G2PIntakeFormSubmissionDocument(BaseORMModel):
    """Junction: documents attached to an intake form submission section (references g2p_registry_documents)."""
    __tablename__ = "g2p_intake_section_documents"

    submission_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    section_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String, nullable=False)


G2PIntakeFormSectionDocuments = G2PIntakeFormSubmissionDocument
