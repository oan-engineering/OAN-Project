import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from openg2p_fastapi_common.models import BaseORMModel


class ImportFileProcessLog(BaseORMModel):
    __tablename__ = "import_file_process_log"

    import_file_record_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    import_file_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )
    record_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ingestion_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index(
            "ux_import_file_process_log_document_id_record_number",
            "document_id",
            "record_number",
            unique=True,
        ),
    )

