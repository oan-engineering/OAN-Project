import uuid
from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel
from datetime import datetime

from .data_models import ProcessStatusEnum

class OutgoingTopic(BaseORMModel):
    
    __tablename__ = "outgoing_topics"
    
    topic_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    websub_topic: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    websub_register_status: Mapped[str] = mapped_column(String, nullable=False, default=ProcessStatusEnum.PENDING.value)
    websub_register_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    websub_register_number_of_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    websub_register_latest_error_code: Mapped[str] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("data_model_id", "register_id", name="uix_dr_outgoing_topics"),
    )

class OutgoingTemplate(BaseORMModel):

    __tablename__ = "outgoing_templates"

    template_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # document_id of the template in g2p_registry_documents (TEMPLATES bucket)
    template_document_id: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('data_model_id', 'register_id', name='uix_dr_outgoing_templates'),
    )
