import uuid
from datetime import datetime
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel

from .g2p_functional_id_generation_queue import ProcessStatusEnum


class G2PCompletionScoreComputationQueue(BaseORMModel):
    __tablename__ = "g2p_completion_score_computation_queue"

    queue_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    change_request_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    submission_id: Mapped[str] = mapped_column(String, nullable=True, index=True)

    compute_status: Mapped[ProcessStatusEnum] = mapped_column(
        String, nullable=False, default=ProcessStatusEnum.PENDING
    )
    compute_number_of_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    compute_processed_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )
    compute_latest_error_code: Mapped[str] = mapped_column(String, nullable=True)
