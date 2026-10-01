import uuid
from sqlalchemy import String, ForeignKey, Boolean, Integer, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class G2PRegisterSection(BaseORMModel):
    """
    Stores section UI schema configurations for each register.
    Primary key: section_id
    """
    __tablename__ = "g2p_register_sections"

    register_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )
    section_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4())
    )
    section_register_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    is_core_section: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    section_mnemonic: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    section_description: Mapped[Text] = mapped_column(Text, nullable=True)
    documents_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    no_of_verifications_required: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_list: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    section_weightage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # JSON structure to define UI rendering for this section
    section_ui_schema: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Auto-approval
    cr_auto_approve_for_bene_portal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cr_auto_approve_for_agent_portal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cr_auto_approve_for_staff_portal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cr_auto_approve_for_partner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    
class G2PRegisterSectionDocument(BaseORMModel):
    """Junction: live documents of a register record section (references g2p_registry_documents)."""
    __tablename__ = "g2p_register_section_documents"

    internal_record_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        index=True
    )
    document_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        index=True
    )
    section_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )
    label: Mapped[str] = mapped_column(String, nullable=False)
