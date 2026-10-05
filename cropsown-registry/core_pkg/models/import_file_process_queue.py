import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from openg2p_fastapi_common.models import BaseORMModel

from .enum import ProcessStatusEnum


class ImportFileProcessQueue(BaseORMModel):
    __tablename__ = "import_file_process_queue"

    import_file_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    document_id: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    intake_form_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    queued_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    queued_by: Mapped[str | None] = mapped_column(String, nullable=True)

    intake_form_ingestion_status: Mapped[ProcessStatusEnum] = mapped_column(
        String, nullable=False, default=ProcessStatusEnum.PENDING, index=True
    )
    intake_form_ingestion_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    intake_form_ingestion_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    intake_form_ingestion_error: Mapped[str | None] = mapped_column(
        String, nullable=True
    )

    number_of_records_present: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    number_of_records_ingested: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

