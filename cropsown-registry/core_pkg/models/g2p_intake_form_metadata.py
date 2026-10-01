import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class G2PIntakeFormDefinition(BaseORMModel):
    __tablename__ = "g2p_intake_form_definitions"

    form_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    form_mnemonic: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    form_description: Mapped[Text] = mapped_column(Text, nullable=True)
    number_of_verifications: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_only_in_ingestion_pipeline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class G2PIntakeFormUITab(BaseORMModel):
    __tablename__ = "g2p_intake_form_ui_tabs"

    tab_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    form_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    tab_label: Mapped[str] = mapped_column(String, nullable=False)
    tab_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class G2PIntakeFormUITabSection(BaseORMModel):
    __tablename__ = "g2p_intake_form_ui_tab_sections"

    tab_section_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tab_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
