import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class G2PRegisterScoreHistory(BaseORMModel):
    """
    Immutable snapshot of computed scores (append-only).
    """

    __tablename__ = "g2p_register_score_history"

    internal_record_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    score_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    score_definition_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    link_internal_record_id: Mapped[str] = mapped_column(String, nullable=True, index=True)

    triggered_by_cr_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    triggered_by_submission_id: Mapped[str] = mapped_column(String, nullable=True, index=True)

    computed_score: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index(
            "ix_g2p_register_score_history_link_rec_id_score_type",
            "link_internal_record_id",
            "score_type",
        ),
    )

