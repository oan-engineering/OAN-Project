import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text, JSON, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel

from .enum import ApprovalStatusEnum, ChangeRequestSourceEnum, DeduplicationStatusEnum

class G2PRegisterChangeRequest(BaseORMModel):
    __tablename__ = "g2p_register_change_requests"

    change_request_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    record_name: Mapped[str] = mapped_column(String, nullable=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    tab_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    no_of_verifications_required: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    no_of_verifications_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Deduplication
    deduplication_register_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=DeduplicationStatusEnum.PENDING.value,
        index=True
    )
    deduplication_register_failure_reason: Mapped[str] = mapped_column(String, nullable=True)
    deduplication_change_request_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=DeduplicationStatusEnum.PENDING.value,
        index=True
    )
    deduplication_change_request_failure_reason: Mapped[str] = mapped_column(String, nullable=True)

    # Audit Trails
    remarks: Mapped[str] = mapped_column(Text, nullable=True)
    approval_status: Mapped[str] = mapped_column(String, nullable=False, default=ApprovalStatusEnum.PENDING.value)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    approved_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    approved_by: Mapped[str] = mapped_column(String, nullable=True)

    change_request_source: Mapped[ChangeRequestSourceEnum] = mapped_column(String, nullable=False)
    # master data PARTNER_ID
    source_partner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Set after async callback to AWE (external correlation id and status summary).
    awe_request_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    awe_request_status_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class G2PRegisterChangeRequestPayload(BaseORMModel):
    __tablename__ = "g2p_register_change_request_payloads"

    change_request_id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    change_payload: Mapped[JSON] = mapped_column(JSON, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index('ix_g2p_register_change_request_payloads_search_text_gin', 'search_text', postgresql_using='gin', postgresql_ops={'search_text': 'gin_trgm_ops'}),
    )

class G2PRegisterChangeRequestDocument(BaseORMModel):
    """Junction: documents attached to a change request (references g2p_registry_documents)."""
    __tablename__ = "g2p_change_request_documents"

    change_request_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    section_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
