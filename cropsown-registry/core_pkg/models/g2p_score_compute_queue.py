import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Index
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel

from .g2p_functional_id_generation_queue import ProcessStatusEnum


class G2PScoreComputeQueue(BaseORMModel):
    """
    Queue items for asynchronously computing scores for a given
    (link_internal_record_id, score_type) after Change Request approval.
    """

    __tablename__ = "g2p_score_compute_queue"

    queue_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    link_internal_record_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    score_definition_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    score_type: Mapped[str] = mapped_column(String, nullable=False, index=True)

    change_request_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    submission_id: Mapped[str] = mapped_column(String, nullable=True, index=True)

    # Snapshot of contributing attribute values at time of CR approval
    contributing_attribute_values: Mapped[JSON] = mapped_column(JSON, nullable=False)

    # Processing status + retry tracking
    compute_status: Mapped[ProcessStatusEnum] = mapped_column(
        String,
        nullable=False,
        default=ProcessStatusEnum.PENDING,
        index=True,
    )
    compute_no_of_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compute_latest_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    compute_latest_error_code: Mapped[str] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index(
            "ix_g2p_score_compute_queue_link_rec_id_score_type_status",
            "link_internal_record_id",
            "score_type",
            "compute_status",
        ),
    )

