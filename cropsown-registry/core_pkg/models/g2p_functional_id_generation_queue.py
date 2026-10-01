import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class ProcessStatusEnum(str, enum.Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class G2PFunctionalIdGenerationQueue(BaseORMModel):
    __tablename__ = "g2p_functional_id_generation_queue"

    queue_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # resolved id and affix
    resolved_id: Mapped[str] = mapped_column(String, nullable=True)
    resolved_prefix: Mapped[str] = mapped_column(String, nullable=True)
    resolved_suffix: Mapped[str] = mapped_column(String, nullable=True)

    # id allocation processing
    id_allocation_status: Mapped[ProcessStatusEnum] = mapped_column(String, nullable=False, default=ProcessStatusEnum.PENDING)
    id_allocation_no_of_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    id_allocation_latest_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    id_allocation_latest_error_code: Mapped[str] = mapped_column(String, nullable=True)

    # id updation processing
    id_updation_status: Mapped[ProcessStatusEnum] = mapped_column(String, nullable=False, default=ProcessStatusEnum.NOT_APPLICABLE)
    id_updation_no_of_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    id_updation_latest_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    id_updation_latest_error_code: Mapped[str] = mapped_column(String, nullable=True)
