import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class G2PRegisterSectionCompletionScore(BaseORMModel):
    __tablename__ = "g2p_register_section_completion_score"
    __table_args__ = (
        UniqueConstraint(
            "register_id",
            "internal_record_id",
            "section_id",
            name="uq_section_completion_score",
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    computed_section_completion_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    computed_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
